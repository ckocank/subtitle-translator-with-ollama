#!/usr/bin/env python3
"""
Subtitle Translator - Translates SRT subtitle files using Ollama
Usage: python translate_subtitle.py <subtitle_file.srt> [options]
"""

import re
import sys
import time
import argparse
import requests
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


# ── Configuration ──────────────────────────────────────────────────────────────

OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL       = "translategemma:4b"
CHUNK_SIZE  = 30          # subtitle blocks per request
MAX_RETRIES = 3
RETRY_DELAY = 2           # seconds between retries

# Language name → output file suffix
LANGUAGE_SUFFIXES = {
    "vietnamese":   "vie",
    "english":      "eng",
    "french":       "fre",
    "spanish":      "spa",
    "german":       "ger",
    "italian":      "ita",
    "portuguese":   "por",
    "japanese":     "jpn",
    "korean":       "kor",
    "chinese":      "zho",
    "thai":         "tha",
    "indonesian":   "ind",
    "arabic":       "ara",
    "russian":      "rus",
    "hindi":        "hin",
}

DEFAULT_LANGUAGE = "vietnamese"


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class SubtitleBlock:
    index: str
    timestamp: str
    text: list

    def to_srt(self) -> str:
        return f"{self.index}\n{self.timestamp}\n" + "\n".join(self.text) + "\n"


# ── SRT Parser ─────────────────────────────────────────────────────────────────

def parse_srt(content: str) -> list:
    """Parse raw SRT text into a list of SubtitleBlock objects."""
    blocks = []
    raw_blocks = re.split(r"\n\s*\n", content.strip())

    for raw in raw_blocks:
        lines = raw.strip().splitlines()
        if len(lines) < 3:
            continue
        index_line = lines[0].strip()
        ts_line    = lines[1].strip()
        text_lines = [l.rstrip() for l in lines[2:]]
        blocks.append(SubtitleBlock(index=index_line, timestamp=ts_line, text=text_lines))

    return blocks


def blocks_to_srt(blocks: list) -> str:
    return "\n".join(b.to_srt() for b in blocks) + "\n"


# ── Chunking ───────────────────────────────────────────────────────────────────

def chunk_blocks(blocks: list, size: int) -> list:
    return [blocks[i : i + size] for i in range(0, len(blocks), size)]


# ── Ollama Translation ─────────────────────────────────────────────────────────

def build_prompt(blocks: list, language: str) -> str:
    """Build the translation prompt for a chunk of subtitle blocks."""
    numbered_lines = []
    for b in blocks:
        text = " / ".join(b.text)
        numbered_lines.append(f"[{b.index}] {text}")

    entries = "\n".join(numbered_lines)

    return (
        f"You are a professional subtitle translator. "
        f"Translate the following subtitle lines from their original language into natural, fluent {language.title()}. "
        f"Keep the same numbering format [N]. "
        f"Return ONLY the translated lines, one per subtitle, using the exact same [N] prefix. "
        f"Do NOT add any explanation, notes, or extra text.\n\n"
        f"{entries}"
    )


def call_ollama(prompt: str, model: str) -> str:
    """Call the Ollama API and return the generated text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 2048,
        }
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    if not response.ok:
        try:
            err_body = response.json()
            err_msg = err_body.get("error", response.text)
        except Exception:
            err_msg = response.text
        raise RuntimeError(f"Ollama {response.status_code}: {err_msg}  (model='{model}')")
    data = response.json()
    return data.get("response", "").strip()


def parse_translated_response(response: str, original_blocks: list) -> list:
    """
    Parse model output back into SubtitleBlock objects.
    Falls back to the original text if a block's translation is missing.
    """
    translation_map = {}
    for line in response.splitlines():
        line = line.strip()
        m = re.match(r"\[(\d+)\]\s*(.*)", line)
        if m:
            idx, text = m.group(1), m.group(2).strip()
            translation_map[idx] = text

    translated = []
    for block in original_blocks:
        tr_text = translation_map.get(block.index)
        if tr_text:
            if len(block.text) > 1 and " / " in tr_text:
                text_lines = tr_text.split(" / ")
            else:
                text_lines = [tr_text]
        else:
            text_lines = block.text   # fallback to original
        translated.append(SubtitleBlock(index=block.index, timestamp=block.timestamp, text=text_lines))

    return translated


def translate_chunk(blocks: list, chunk_num: int, total: int, model: str, language: str) -> list:
    """Translate a single chunk with retry logic."""
    prompt = build_prompt(blocks, language)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  Chunk {chunk_num}/{total} — attempt {attempt} ... ", end="", flush=True)
            t0 = time.time()
            raw = call_ollama(prompt, model)
            elapsed = time.time() - t0
            print(f"done ({elapsed:.1f}s)")
            return parse_translated_response(raw, blocks)
        except requests.exceptions.ConnectionError:
            print(f"\n  ✗ Cannot connect to Ollama at {OLLAMA_URL}")
            print("    Make sure Ollama is running: ollama serve")
            sys.exit(1)
        except Exception as e:
            print(f"failed: {e}")
            if attempt < MAX_RETRIES:
                print(f"    Retrying in {RETRY_DELAY}s…")
                time.sleep(RETRY_DELAY)
            else:
                print(f"  ✗ Chunk {chunk_num} failed after {MAX_RETRIES} attempts. Keeping original text.")
                return blocks


# ── Progress display ───────────────────────────────────────────────────────────

def progress_bar(current: int, total: int, width: int = 40) -> str:
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = 100 * current // total
    return f"[{bar}] {pct:3d}%  ({current}/{total} chunks)"


# ── Output filename helper ─────────────────────────────────────────────────────

def make_output_path(src: Path, language: str) -> Path:
    """Generate output filename: <stem>.<lang_suffix>.srt"""
    suffix = LANGUAGE_SUFFIXES.get(language.lower(), language.lower()[:3])
    return src.with_name(src.stem + f".{suffix}.srt")


# ── Main logic ─────────────────────────────────────────────────────────────────

def translate_file(
    input_path: str,
    chunk_size: int,
    output_path: Optional[str],
    model: str,
    language: str,
) -> None:
    src = Path(input_path)
    if not src.exists():
        print(f"Error: file not found — {input_path}")
        sys.exit(1)
    if src.suffix.lower() != ".srt":
        print("Warning: file does not have a .srt extension, proceeding anyway.")

    dst = Path(output_path) if output_path else make_output_path(src, language)

    print(f"\n{'─'*60}")
    print(f"  Subtitle Translator  (Ollama · {model})")
    print(f"{'─'*60}")
    print(f"  Input    : {src}")
    print(f"  Output   : {dst}")
    print(f"  Language : {language.title()}")
    print(f"  Chunk    : {chunk_size} blocks/request")
    print(f"{'─'*60}\n")

    content = src.read_text(encoding="utf-8", errors="replace")
    blocks  = parse_srt(content)
    print(f"  Parsed {len(blocks)} subtitle blocks.\n")

    if not blocks:
        print("No subtitle blocks found. Check the file format.")
        sys.exit(1)

    chunks = chunk_blocks(blocks, chunk_size)
    total  = len(chunks)
    print(f"  Translating {total} chunk(s)…\n")

    translated_blocks = []
    start = time.time()

    for i, chunk in enumerate(chunks, 1):
        result = translate_chunk(chunk, i, total, model, language)
        translated_blocks.extend(result)
        print(f"  {progress_bar(i, total)}\n")

    elapsed = time.time() - start
    print(f"\n  ✓ Translation complete in {elapsed:.1f}s")

    output_srt = blocks_to_srt(translated_blocks)
    dst.write_text(output_srt, encoding="utf-8")
    print(f"  ✓ Saved → {dst}\n")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    # Build the language list for help text
    lang_list = ", ".join(sorted(LANGUAGE_SUFFIXES.keys()))

    parser = argparse.ArgumentParser(
        description="Translate SRT subtitle files using Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python translate_subtitle.py movie.srt
  python translate_subtitle.py movie.srt --language french
  python translate_subtitle.py movie.srt --language japanese
  python translate_subtitle.py movie.srt --language spanish --output movie.es.srt
  python translate_subtitle.py movie.srt --chunk-size 20 --model gemma:4b

Supported languages (built-in suffixes):
  {lang_list}

  Any other language name is also accepted — the first 3 letters become the file suffix.
  Example: --language swahili  →  movie.swa.srt

Requirements:
  - Ollama running locally  (ollama serve)
  - Model pulled            (ollama pull gemma:4b)
  - requests library        (pip install requests)
        """,
    )
    parser.add_argument("input", help="Path to the input .srt subtitle file")
    parser.add_argument(
        "--language", "-l",
        default=DEFAULT_LANGUAGE,
        metavar="LANG",
        help=f"Target language for translation (default: {DEFAULT_LANGUAGE})",
    )
    parser.add_argument(
        "--chunk-size", "-c",
        type=int,
        default=CHUNK_SIZE,
        metavar="N",
        help=f"Number of subtitle blocks per translation request (default: {CHUNK_SIZE})",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        metavar="FILE",
        help="Custom output file path (default: auto-generated from language)",
    )
    parser.add_argument(
        "--model", "-m",
        default=MODEL,
        metavar="MODEL",
        help=f"Ollama model name (default: {MODEL})",
    )

    args = parser.parse_args()
    translate_file(args.input, args.chunk_size, args.output, args.model, args.language)


if __name__ == "__main__":
    main()
