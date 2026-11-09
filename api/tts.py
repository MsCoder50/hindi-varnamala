from http.server import BaseHTTPRequestHandler
import urllib.parse
import asyncio
import edge_tts

# Pure vowel sound mapping for combining matras - zero "की मात्रा"
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

DEFAULT_VOICE = "hi-IN-SwaraNeural"

async def generate_speech(text: str, voice: str, rate: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    buffer = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.extend(chunk["data"])
    return bytes(buffer)

class handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # Serve index.html if root is requested
        if parsed.path in ('/', '/index.html', ''):
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            index_path = os.path.join(base_dir, 'index.html')
            if not os.path.exists(index_path):
                index_path = os.path.join(os.getcwd(), 'index.html')
            if os.path.exists(index_path):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'public, max-age=3600')
                self.end_headers()
                with open(index_path, 'rb') as f:
                    self.wfile.write(f.read())
                return

        # Serve local audio files if requested via /audio/...
        if parsed.path.startswith('/audio/'):
            import os
            rel = urllib.parse.unquote(parsed.path.lstrip('/'))
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            audio_path = os.path.join(base_dir, rel)
            if not os.path.exists(audio_path):
                audio_path = os.path.join(os.getcwd(), rel)
            if os.path.exists(audio_path):
                self.send_response(200)
                self.send_header('Content-Type', 'audio/mpeg')
                self.send_header('Cache-Control', 'public, max-age=604800, immutable')
                self.end_headers()
                with open(audio_path, 'rb') as f:
                    self.wfile.write(f.read())
                return

        # Health check
        if parsed.path.endswith('/status') or parsed.path.endswith('/health') or params.get('health'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status":"ok","engine":"edge-tts-serverless","voice":"hi-IN-SwaraNeural"}')
            return

        text = params.get('text', [''])[0].strip()
        voice = params.get('voice', [DEFAULT_VOICE])[0].strip()

        if not text:
            self.send_response(400)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'Missing text parameter')
            return

        raw = text.replace('◌', '').strip()
        rate_val = "+0%"

        # Precise timing for short vs long vowels
        if raw in ('इ', 'ि'):
            prompt_text = "इ"
            rate_val = "+25%"  # Short crisp [ɪ]
        elif raw in ('उ', 'ु'):
            prompt_text = "उ"
            rate_val = "+25%"  # Short crisp [ʊ]
        elif raw in ('ई', 'ी'):
            prompt_text = "ई"
            rate_val = "-15%"  # Sustained long [iː]
        elif raw in ('ऊ', 'ू'):
            prompt_text = "ऊ"
            rate_val = "-15%"  # Sustained long [uː]
        elif raw in ('आ', 'ा'):
            prompt_text = "आ"
            rate_val = "-10%"
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

        try:
            audio_bytes = asyncio.run(generate_speech(prompt_text, voice, rate_val))
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'public, max-age=604800, immutable')
            self.end_headers()
            self.wfile.write(audio_bytes)
        except Exception as e:
            self.send_response(500)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"TTS Error: {e}".encode('utf-8'))
