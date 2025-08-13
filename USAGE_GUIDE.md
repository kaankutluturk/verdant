# 📖 Verdant Usage Guide

> **Complete guide to using Verdant - the eco-conscious local AI assistant.**

## 🚀 Quick Start

### GUI (recommended)
```bash
# Windows packaged app
VerdantApp.exe
# Or from source
python verdant_app.py
```
- First launch shows onboarding: Run Setup to download the model (~3.8GB) or enable Instant Demo (no download).
- Use Settings (⚙) to adjust Temperature, Top‑p, and Context (capped in demo).
- Try preset buttons: Paraphrase, Grammar fix, Summarize, Citation.

### CLI
```bash
pip install -r requirements.txt
python test_verdant.py
python verdant.py --setup
python verdant.py --interactive
```

> **💡 Environmental Note**: See [README.md](README.md) for Verdant's eco benefits.

## 📚 Detailed Usage

### Setup Commands
```bash
python verdant.py --setup
python verdant.py --setup --model mistral-7b-q4
```

### Interactive Mode
```bash
python verdant.py --interactive
python verdant.py --interactive --model mistral-7b-q4
```

### Single Prompt
```bash
python verdant.py --prompt "Your question here"
python verdant.py --prompt "Your question" --model mistral-7b-q4
```

### Presets
- GUI: Use sidebar buttons or type your prompt; selected preset will be prepended automatically.
- CLI: `--preset paraphrase_academic|grammar_fix|concise_summary|citation_check` combined with `--prompt`.

### Sessions
- GUI: Save/Load chat as JSON from the sidebar.
- CLI: `--load-session session.json` and `--save-session session.json`.

### Benchmark
- GUI: Click Benchmark in the header to run a quick tok/s check.
- CLI: `--benchmark --benchmark-runs 1`.

### Instant Demo Mode
- GUI: Enable in Settings to try the app without downloading a model (canned streaming responses for a quick feel).

## ⚙️ Performance Optimization

### Automatic Hardware Detection
Verdant detects RAM and CPU to set threads and context.

- High (16GB+ RAM, 8+ cores): 4096 context
- Medium (8GB+ RAM, 4+ cores): 2048 context
- Low (<8GB RAM): 1024 context

### Manual Tuning
```bash
python verdant.py --interactive --threads 8 --context 4096
python verdant.py --interactive --threads 4 --context 1024
```
In GUI, adjust in Settings. Demo builds cap context per capabilities.

## 🔧 Troubleshooting

- "llama-cpp-python not installed": `pip install llama-cpp-python`
- "Model not found": run Setup or enable Instant Demo in Settings.
- Slow performance: close other apps; reduce Context and Temperature.

## 📝 Advanced Usage

- Batch prompts (CLI):
```bash
python verdant.py --prompt "First" 
python verdant.py --prompt "Second"
```
- Academic writing assistant (CLI):
```bash
python verdant.py --preset paraphrase_academic --prompt "Improve this paragraph: ..."
```

## 🏗️ Project Structure
```
verdant/
├── verdant.py              # CLI core
├── verdant_gui.py          # GUI app
├── verdant_app.py          # GUI/CLI launcher
├── requirements.txt
├── README.md
├── USAGE_GUIDE.md
├── PROJECT_STATUS.md
└── examples/
```

## 💰 Full Experience
- Larger contexts, additional models, and GPU support are planned for premium builds.

## 🎯 Support
- Issues on GitHub. Docs here and in README. 