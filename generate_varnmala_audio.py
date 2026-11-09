#!/usr/bin/env python3
"""
Hindi Varnamala Audio Generator
Generates studio-quality MP3 audio files using Microsoft's Swara Neural Voice
for completely offline, crystal-clear playback in the Hindi Varnamala Game.

Usage:
  python3 generate_varnmala_audio.py
"""

import os
import sys
import asyncio

try:
    import edge_tts
except ImportError:
    print("[INFO] 'edge-tts' package is not installed. Setting up...")
    import subprocess
    installed = False

    # Method 1: Try with --break-system-packages (Debian/Ubuntu Python 3.13 PEP 668)
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
            print("[INFO] Restarting script inside .venv...")
            os.execv(venv_python, [venv_python] + sys.argv)
        except Exception as e:
            print(f"\n[ERROR] Setup failed: {e}")
            print("\nकृपया टर्मिनल में यह कमांड चलाएँ:")
            print("  pip install --break-system-packages edge-tts")
            print("अथवा:")
            print(f"  python3 -m venv .venv && .venv/bin/pip install edge-tts && .venv/bin/python {sys.argv[0]}\n")
            sys.exit(1)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
VOICE = "hi-IN-SwaraNeural"

# List of all foundational Swar, Vyanjan, and practice words
SWAR = ["अ", "आ", "इ", "ई", "उ", "ऊ", "ऋ", "ए", "ऐ", "ओ", "औ", "अं", "अः"]

VYANJAN = [
    "क", "ख", "ग", "घ", "ङ",
    "च", "छ", "ज", "झ", "ञ",
    "ट", "ठ", "ड", "ढ", "ण",
    "त", "थ", "द", "ध", "न",
    "प", "फ", "ब", "भ", "म",
    "य", "र", "ल", "व",
    "श", "ष", "स", "ह",
    "क्ष", "त्र", "ज्ञ", "श्र"
]

BARAHKHADI_CONSONANTS = ['क', 'ख', 'ग', 'घ', 'च', 'छ', 'ज', 'झ', 'ट', 'ठ', 'ड', 'ढ', 'त', 'थ', 'द', 'ध', 'न', 'प', 'फ', 'ब', 'भ', 'म', 'य', 'र', 'ल', 'व', 'श', 'ष', 'स', 'ह']
BARAHKHADI_MATRAS = ['', 'ा', 'ि', 'ी', 'ु', 'ू', 'े', 'ै', 'ो', 'ौ', 'ं', 'ः']

WORDS = [
    "जल", "घर", "कल", "रथ", "फल", "धन", "नल", "मन", "छत", "खत",
    "कमल", "मटर", "नमक", "सड़क", "कलम", "भगत", "नहर", "मगर", "भवन",
    "अदरक", "बरगद", "कसरत", "अचकन", "शरबत", "बर्तन", "टमटम", "खटमल"
]

# Matras mapping to ONLY pure vowel sounds - zero "की मात्रा" words!
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

# Phonetic prompt improvements for edge-tts
PRONUNCIATION_MAP = {
    "ऋ": "री",
    "ज्ञ": "ग्या",
    "ङ": "अंग",
    "ञ": "इयाँ",
    "अं": "अंग",
    "अः": "अह"
}

async def generate_single(text, filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(filepath):
        return  # Skip already generated

    raw = text.replace("◌", "").strip()
    rate_val = "+0%"

    if raw in ("इ", "ि"):
        prompt_text = "इ"
        rate_val = "+25%"  # Crisp short [ɪ]
    elif raw in ("उ", "ु"):
        prompt_text = "उ"
        rate_val = "+25%"  # Crisp short [ʊ]
    elif raw in ("ई", "ी"):
        prompt_text = "ई"
        rate_val = "-15%"  # Sustained long [iː]
    elif raw in ("ऊ", "ू"):
        prompt_text = "ऊ"
        rate_val = "-15%"  # Sustained long [uː]
    elif raw in ("आ", "ा"):
        prompt_text = "आ"
        rate_val = "-10%"
    elif raw == "अ":
        prompt_text = "अ"
        rate_val = "+10%"
    elif raw in MATRA_MAP:
        prompt_text = MATRA_MAP[raw]
    else:
        prompt_text = PRONUNCIATION_MAP.get(text, text)
        if text.endswith("ः") and len(text) >= 2:
            prompt_text = text[:-1] + "ह"

    communicate = edge_tts.Communicate(prompt_text, VOICE, rate=rate_val)
    await communicate.save(filepath)

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_items = []

    # 1. Swar
    for s in SWAR:
        all_items.append((s, f"{s}.mp3"))

    # 2. Vyanjan
    for v in VYANJAN:
        all_items.append((v, f"{v}.mp3"))

    # 3. Matras
    for m in MATRA_MAP.keys():
        all_items.append((m, f"{m}.mp3"))
        all_items.append((f"◌{m}", f"◌{m}.mp3"))

    # 4. Barahkhadi
    for c in BARAHKHADI_CONSONANTS:
        for m in BARAHKHADI_MATRAS:
            item = c + m
            all_items.append((item, f"{item}.mp3"))

    # 5. Words
    for w in WORDS:
        all_items.append((w, f"{w}.mp3"))

    total = len(all_items)
    print(f"🎙️ Starting audio generation for {total} items using {VOICE}...")
    
    success = 0
    for idx, (item, fname) in enumerate(all_items, 1):
        try:
            await generate_single(item, fname)
            success += 1
            if idx % 20 == 0 or idx == total:
                print(f"[{idx}/{total}] Generated {success} audio files...")
        except Exception as e:
            print(f"Error generating '{item}': {e}")
        # Brief pause to respect API rate limits
        await asyncio.sleep(0.05)

    print(f"✅ Finished! Audio files saved in: {OUTPUT_DIR}")

if __name__ == "__main__":
    asyncio.run(main())
