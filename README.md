# Subtitle Translator

Translate SRT subtitle files into any language using Ollama's local AI models. Fast, private, and works completely offline.

## Features

- 🌍 **Multi-language support** — Translate to Vietnamese, English, French, Spanish, Japanese, Korean, Chinese, and 8+ more languages
- 📦 **Smart chunking** — Automatically splits large subtitle files into manageable pieces
- 🔄 **Auto-retry** — Retries failed chunks up to 3 times before falling back to original text
- 💾 **Preserves timing** — All timestamps remain intact, only text is translated
- 🚀 **Progress tracking** — Real-time progress bar and per-chunk timing
- 🔒 **100% local** — No data leaves your machine, no API keys required

## Requirements

1. **Ollama** — Download and install from [ollama.com](https://ollama.com)
2. **Python 3.8+** 
3. **requests** library:
   ```bash
   pip install requests
   ```

## Installation

1. Clone or download `translate_subtitle.py`
2. Make sure Ollama is running:
   ```bash
   ollama serve
   ```
3. Pull a translation model:
   ```bash
   ollama pull gemma:4b
   ```

## Quick Start

Translate to Vietnamese (default):
```bash
python translate_subtitle.py movie.srt
```
Output: `movie.vie.srt`

Translate to another language:
```bash
python translate_subtitle.py movie.srt --language french
```
Output: `movie.fre.srt`

## Usage

```
python translate_subtitle.py <input.srt> [options]
```

### Options

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--language` | `-l` | Target language for translation | `vietnamese` |
| `--chunk-size` | `-c` | Number of subtitle blocks per API call | `30` |
| `--output` | `-o` | Custom output file path | Auto-generated |
| `--model` | `-m` | Ollama model to use | `gemma:4b` |

### Examples

**Basic translation:**
```bash
python translate_subtitle.py movie.srt
```

**Translate to Japanese:**
```bash
python translate_subtitle.py movie.srt --language japanese
# Creates: movie.jpn.srt
```

**Custom output path:**
```bash
python translate_subtitle.py movie.srt -l spanish -o my_movie_spanish.srt
```

**Smaller chunks (more reliable, slower):**
```bash
python translate_subtitle.py movie.srt --chunk-size 15
```

**Different model:**
```bash
python translate_subtitle.py movie.srt --model llama3:8b
```

## Supported Languages

The script includes built-in file suffixes for these languages:

- Vietnamese (`vie`)
- English (`eng`)
- French (`fre`)
- Spanish (`spa`)
- German (`ger`)
- Italian (`ita`)
- Portuguese (`por`)
- Japanese (`jpn`)
- Korean (`kor`)
- Chinese (`zho`)
- Thai (`tha`)
- Indonesian (`ind`)
- Arabic (`ara`)
- Russian (`rus`)
- Hindi (`hin`)

**Any other language is also supported** — the script will use the first 3 letters as the file suffix. For example:
```bash
python translate_subtitle.py movie.srt --language swahili
# Creates: movie.swa.srt
```

## How It Works

1. **Parse** — Reads the SRT file and extracts subtitle blocks (index, timestamp, text)
2. **Chunk** — Splits subtitles into groups (default: 30 blocks per chunk)
3. **Translate** — Sends each chunk to Ollama with a strict prompt format
4. **Reassemble** — Combines translated blocks back into proper SRT format
5. **Save** — Writes output to `<filename>.<language>.srt`

Each chunk is translated independently, so if one fails, the rest continue. Failed chunks keep their original text as a fallback.

## Troubleshooting

### `Cannot connect to Ollama`
Make sure Ollama is running:
```bash
ollama serve
```

### `Ollama 404: model not found`
Pull the model first:
```bash
ollama pull gemma:4b
```

Check available models:
```bash
ollama list
```

### Translation quality is poor
Try a larger model:
```bash
ollama pull llama3:8b
python translate_subtitle.py movie.srt --model llama3:8b
```

### Translations are getting cut off
Reduce chunk size to give the model more context per subtitle:
```bash
python translate_subtitle.py movie.srt --chunk-size 15
```

### Script is slow
Increase chunk size (less API calls, but higher memory usage):
```bash
python translate_subtitle.py movie.srt --chunk-size 50
```

## Performance Tips

- **Chunk size:** Start with 30. If you get incomplete translations, reduce to 15-20. For simple subtitles, try 50.
- **Model choice:** `gemma:4b` is fast. `llama3:8b` is more accurate but slower. `mixtral:8x7b` is best quality but requires more RAM.
- **Batch processing:** Use a shell loop to translate multiple files:
  ```bash
  for file in *.srt; do
    python translate_subtitle.py "$file" --language french
  done
  ```

## File Format

The output preserves the exact SRT structure:
```
1
00:00:01,000 --> 00:00:03,500
[Translated text appears here]

2
00:00:04,000 --> 00:00:06,000
[Next translated line]
```

All timing codes, line breaks, and block numbering remain identical to the source file.

## Privacy & Offline Use

Everything runs locally on your machine:
- No data is sent to external servers
- No API keys required
- Works completely offline (after model download)
- Your subtitle content never leaves your computer

## License

Free to use, modify, and distribute. No warranty provided.

## Credits

Built with:
- [Ollama](https://ollama.com) — Local AI model runtime
- Python 3 — Core language
- [requests](https://requests.readthedocs.io/) — HTTP library

---

**Need help?** Open an issue or check [Ollama's documentation](https://github.com/ollama/ollama/blob/main/docs/README.md) for model-specific questions.
