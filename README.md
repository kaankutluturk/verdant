<p align="left">
  <img src="https://img.shields.io/badge/Verdant-Local%20AI-5BD174?style=for-the-badge&labelColor=0F1214&color=5BD174" alt="Verdant"/>
</p>

# Verdant - Eco-Conscious Local AI

> **The world's first truly green AI assistant. Runs entirely on your device, using 95% less energy than cloud AI while helping you make eco-friendly choices.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Status: MVP](https://img.shields.io/badge/status-MVP-orange.svg)]()

**Website**: [https://kaankutluturk.github.io/verdant/](https://kaankutluturk.github.io/verdant/)

## Download (Windows)

- [Download VerdantApp.exe](https://github.com/kaankutluturk/verdant/releases/latest/download/VerdantApp.exe)
- Run VerdantApp.exe (GUI by default). For CLI, run: `VerdantApp.exe --cli`
- First-time setup downloads the model (one-time)

> Prefer manual install or macOS/Linux? See below.

## What is Verdant?

Verdant is the world's first eco-conscious AI assistant that runs entirely on your device. Built for environmentally conscious students and developers who want powerful AI without the massive carbon footprint of cloud computing.

**Core Values:**
- **🌱 Eco-Conscious**: 95% less energy usage than cloud AI
- **🌍 Carbon-Neutral**: Zero server emissions after setup
- **💚 Sustainable**: One-time setup, lifetime eco-friendly use
- **🚀 High-Performance**: Optimized for your hardware
- **🎓 Academic Focus**: Built specifically for educational tasks

## Why Choose Verdant?

**Traditional AI = Massive Carbon Footprint:**
- Cloud servers running 24/7
- Data centers consuming gigawatts
- Network infrastructure emissions
- Continuous energy waste

**Verdant = Truly Green AI:**
- Runs only when you need it
- Zero server emissions
- Local processing efficiency
- Sustainable by design

## Core Capabilities

**AI Inference:**
- Mistral 7B Instruct (Q4 quantized) running locally
- llama.cpp integration for efficient performance
- Hardware-optimized settings based on your system

**Hardware Detection:**
- Automatic RAM and CPU detection
- Dynamic configuration for optimal performance
- Performance tier classification (High/Medium/Low)

**User Interface:**
- Modern GUI with chat, streaming, Stop/Regenerate
- Preset quick actions and sample prompts
- Save/Load sessions (JSON), Export transcript, Copy all
- Built-in Benchmark (tok/s), Eco meter estimate
- Onboarding flow, About dialog
- Command-line interface also available

## Quick Start (manual install)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Test installation
python test_verdant.py

# 3. Download model (one-time, ~4GB)
python verdant.py --setup

# 4. Start GUI
python verdant_app.py

# Or start CLI
python verdant.py --interactive
```

## Performance

| Hardware Tier | RAM | CPU | Context | Speed |
|---------------|-----|-----|---------|-------|
| **High** | 16GB+ | 8+ cores | 4096 | ~15 tok/sec |
| **Medium** | 8GB+ | 4+ cores | 2048 | ~8 tok/sec |
| **Low** | <8GB | Any | 1024 | ~4 tok/sec |

## Academic Tasks

Verdant excels at common academic writing tasks:

- **Paraphrasing**: Rewrite text in different styles
- **Grammar Fixing**: Correct spelling and punctuation
- **Style Adjustment**: Switch between formal and casual tones
- **Summarization**: Condense long texts
- **Citation Help**: Format references properly

## Installation

### Option 1: Quick Install
```bash
git clone https://github.com/kaankutluturk/verdant.git
cd verdant && pip install -r requirements.txt && python verdant.py --setup
```

### Option 2: Manual Install
```bash
pip install llama-cpp-python psutil requests
python verdant.py --setup
```

## Usage

### GUI
```bash
python verdant_app.py
```
- Settings: adjust Temperature, Top‑p, and Context (demo cap enforced)
- Presets: Paraphrase, Grammar fix, Summarize, Citation
- Benchmark: quick tok/s check
- Instant Demo: try without model download

### CLI
```bash
python verdant.py --interactive
python verdant.py --prompt "Your question here"
python verdant.py --preset paraphrase_academic --prompt "Improve this paragraph: ..."
python verdant.py --benchmark --benchmark-runs 1
```

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   User      │───▶│  Verdant Core │───▶│  Mistral    │
│  (GUI/CLI)  │    │  (Hardware   │    │  7B-Q4     │
│             │    │   Detection) │    │  (llama.cpp)│
└─────────────┘    └──────────────┘    └─────────────┘
```

**Technology Stack:**
- **Model**: Mistral 7B Instruct (4-bit quantized, 3.8GB)
- **Engine**: llama.cpp (optimized C++ implementation)
- **Detection**: Python psutil + platform detection
- **Interface**: Python GUI + CLI

## 🌱 Environmental Impact

**Verdant vs Cloud AI - The Environmental Truth:**

### **Cloud AI Environmental Cost:**
- **Energy**: Massive data centers consuming gigawatts 24/7
- **Carbon**: Continuous emissions from server infrastructure
- **Network**: Global data transmission emissions
- **Waste**: Server hardware lifecycle waste
- **Water**: Data center cooling water consumption

### **Verdant Environmental Benefits:**
- **🌱 Energy**: 95% less than cloud inference
- **🌍 Carbon**: Zero emissions after initial download
- **💚 Network**: Zero traffic after setup
- **♻️ Waste**: No server hardware waste
- **💧 Water**: No cooling water consumption
- **🌿 Sustainable**: Uses only your device's existing resources

**Every time you use Verdant instead of cloud AI, you're making an eco-conscious choice that reduces your digital carbon footprint.**

## Development Roadmap

### Phase 1: MVP ✅ Complete
- Core inference engine
- Basic CLI interface
- Hardware optimization
- Model management

### Phase 2: User Experience (in progress)
- GUI interface with onboarding and About dialog
- Preset templates and sample prompts
- Performance benchmarking and eco meter
- User preferences and session management

### Phase 3: Advanced Features (2-3 months)
- Document processing
- Multiple models
- Plugin system

### Phase 4: Premium Features (3+ months)
- Advanced models (13B, 30B)
- Professional tools
- Enhanced performance

## Contributing

We welcome contributions:

- Report bugs and issues
- Suggest new features
- Improve documentation
- Test on different hardware
- Star the repository

## System Requirements

### Minimum
- RAM: 8GB (6GB for model + 2GB for system)
- CPU: 4 cores
- Storage: 5GB free space
- OS: Windows 10+, macOS 10.15+, Ubuntu 18.04+

### Recommended
- RAM: 16GB+
- CPU: 8+ cores
- Storage: 10GB+
- Storage Type: SSD preferred

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "llama-cpp-python not installed" | `pip install llama-cpp-python` |
| "Model not found" | Run Setup in GUI or `python verdant.py --setup` |
| Slow performance | Close other applications; reduce Context/Temperature |

## License

**MIT License** - Simple and clear:
- Personal use
- Educational use
- Modify and share
- No attribution required

## Get the Full Experience

This GitHub version is a demo with basic features.

- Instant Demo for first‑time experience
- Full local performance after one-time download
- Roadmap: larger models, GPU, and pro tools

**Download for Windows**: https://github.com/kaankutluturk/verdant/releases/latest/download/VerdantApp.exe

---

**Built for environmentally conscious students who believe technology should protect our planet, not destroy it.**

**Get Started • [Documentation](USAGE_GUIDE.md) • [Issues](https://github.com/kaankutluturk/verdant/issues)**
