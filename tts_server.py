#!/usr/bin/env python3
"""
Hindi Neural TTS Local Server (Zero-cost, Zero-key Microsoft Edge Neural Voices)
Provides studio-quality Hindi speech to the web game, completely replacing Google TTS.

Voices supported:
  - hi-IN-SwaraNeural  (Female - Natural Indian Teacher voice)
  - hi-IN-MadhurNeural (Male   - Clear, Professional Indian voice)

Usage:
  python3 tts_server.py
  (Runs on http://localhost:5050)
"""

import sys
import os
import asyncio
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

# Auto-check and install edge-tts if not present
try:
    import edge_tts
except ImportError:
    print("[INFO] 'edge-tts' package is not installed. Setting up...")
    import subprocess
    installed = False

    # Method 1: Try with --break-system-packages (standard on modern Debian/Ubuntu)
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", "edge-tts"])
        import edge_tts
        installed = True
    except Exception:
        pass

    # Method 2: If externally managed, create/use a local virtual environment (.venv)
    if not installed:
        venv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv")
        venv_python = os.path.join(venv_dir, "bin", "python")

        print(f"[INFO] Creating virtual environment at {venv_dir}...")
        try:
            import venv
            venv.create(venv_dir, with_pip=True)
            subprocess.check_call([venv_python, "-m", "pip", "install", "edge-tts"])
            print("[INFO] Restarting server inside .venv...")
            os.execv(venv_python, [venv_python] + sys.argv)
        except Exception as e:
            print(f"\n[ERROR] Setup failed: {e}")
            print("\nकृपया टर्मिनल में यह कमांड चलाएँ:")
            print("  pip install --break-system-packages edge-tts")
            print("अथवा:")
            print("  python3 -m venv .venv && .venv/bin/pip install edge-tts && .venv/bin/python tts_server.py\n")
            sys.exit(1)

PORT = 5050
DEFAULT_VOICE = "hi-IN-SwaraNeural"

# ONLY pure vowel sounds for matras - zero "की मात्रा" words!
MATRA_MAP = {
    "ा": "आ",
    "ि": "इ",
    "ी": "ई",
    "ु": "उ",
    "ू": "ऊ",
    "े": "ए",
    "ै": "ऐ",
    "ो": "ओ",
    "ौ": "औ",
    "ृ": "री",
    "ं": "अंग",
    "ः": "अह"
}

PRONUNCIATION_MAP = {
    "ऋ": "री",
    "ज्ञ": "ग्या",
    "ङ": "अंग",
    "ञ": "इयाँ",
    "अं": "अंग",
    "अः": "अह"
}

class TTSRequestHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # Enable CORS for frontend browser requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == '/status' or parsed.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "engine": "Microsoft Edge Neural TTS", "voice": "hi-IN-SwaraNeural"}')
            return

        if parsed.path == '/tts':
            text = params.get('text', [''])[0].strip()
            voice = params.get('voice', [DEFAULT_VOICE])[0].strip()

            if not text:
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'Missing text parameter')
                return

            raw = text.replace('◌', '').strip()
            rate_val = "+0%"

            # Pure short vowels (इ, उ, ि, ु) vs Long vowels (ई, ऊ, ी, ू):
            # Enforce exact rate timing so short vowels sound crisp and never stretch into long vowels
            if raw in ('इ', 'ि'):
                prompt_text = "इ"
                rate_val = "+25%"  # Short, crisp [ɪ] - prevents Azure from dragging it into 'ई'
            elif raw in ('उ', 'ु'):
                prompt_text = "उ"
                rate_val = "+25%"  # Short, crisp [ʊ] - prevents Azure from dragging it into 'ऊ'
            elif raw in ('ई', 'ी'):
                prompt_text = "ई"
                rate_val = "-15%"  # Sustained, long [iː]
            elif raw in ('ऊ', 'ू'):
                prompt_text = "ऊ"
                rate_val = "-15%"  # Sustained, long [uː]
            elif raw in ('आ', 'ा'):
                prompt_text = "आ"
                rate_val = "-10%"  # Sustained, long [aː]
            elif raw == 'अ':
                prompt_text = "अ"
                rate_val = "+10%"
            elif raw in MATRA_MAP:
                prompt_text = MATRA_MAP[raw]
            elif raw in PRONUNCIATION_MAP:
                prompt_text = PRONUNCIATION_MAP[raw]
            elif raw.endswith('ः') and len(raw) >= 2:
                prompt_text = raw[:-1] + 'ह'
            else:
                prompt_text = text

            print(f"[TTS Server] Synthesizing '{text}' -> '{prompt_text}' (rate: {rate_val}) with voice {voice}...")

            async def generate_audio():
                communicate = edge_tts.Communicate(prompt_text, voice, rate=rate_val)
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                return audio_data

            try:
                audio_bytes = asyncio.run(generate_audio())
                self.send_response(200)
                self.send_header('Content-Type', 'audio/mpeg')
                self.send_header('Content-Length', str(len(audio_bytes)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(audio_bytes)
                return
            except Exception as e:
                print(f"[ERROR] Synthesis failed: {e}")
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
                return

        # Default 404
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        # Clean logging
        sys.stderr.write(f"[TTS Server] {self.address_string()} - {format%args}\n")

def run():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, TTSRequestHandler)
    print("=" * 60)
    print(f"🚀 Hindi Neural TTS Server running at http://localhost:{PORT}")
    print(f"   Default Voice: {DEFAULT_VOICE} (Microsoft Swara - Female)")
    print(f"   Alternative : hi-IN-MadhurNeural (Male)")
    print(f"   Test URL    : http://localhost:{PORT}/tts?text=नमस्ते")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped.")
        httpd.server_close()

if __name__ == '__main__':
    run()
