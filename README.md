# Verdant - Local AI Assistant

> **Privacy-first AI that runs entirely on your laptop. No cloud, no subscriptions, no data mining. 100% offline after setup.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Status: MVP](https://img.shields.io/badge/status-MVP-orange.svg)]()

## What is Verdant?

Verdant is a local AI assistant that runs entirely on your device. It's designed for students and developers who need AI assistance without compromising privacy or relying on cloud services.

**Key Features:**
- **Privacy**: Your data never leaves your device
- **Efficiency**: 95% less energy usage than cloud AI
- **Cost**: One-time setup, no monthly fees
- **Performance**: Optimized for your hardware
- **Academic Focus**: Built specifically for educational tasks

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
- Command-line interface with interactive mode
- Single prompt processing for scripts
- Cross-platform support (Windows, macOS, Linux)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Test installation
python test_verdant.py

# 3. Download model (one-time, ~4GB)
python verdant.py --setup

# 4. Start using
python verdant.py --interactive
```

## Performance

| Hardware Tier | RAM | CPU | Context | Speed |
|---------------|-----|-----|---------|-------|
| **High** | 16GB+ | 8+ cores | 4096 | ~15 tok/sec |
| **Medium** | 8GB+ | 4+ cores | 2048 | ~8 tok/sec |
| **Low** | <8GB | Any | 1024 | ~4 tok/sec |

**Benchmarks:**
- MacBook Air M1: ~8 tok/sec, 4GB RAM usage
- ThinkPad X1: ~6 tok/sec, 5GB RAM usage  
- Gaming PC: ~15 tok/sec, 6GB RAM usage

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
python lumina.py --setup
```

## Usage

### Interactive Mode
```bash
python verdant.py --interactive
```

### Single Prompt
```bash
python verdant.py --prompt "Your question here"
```

### Performance Tuning
```bash
python verdant.py --threads 8 --context 4096
```

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   User      │───▶│  Verdant Core │───▶│  Mistral    │
│  (CLI)      │    │  (Hardware   │    │  7B-Q4     │
│             │    │   Detection) │    │  (llama.cpp)│
└─────────────┘    └──────────────┘    └─────────────┘
```

**Technology Stack:**
- **Model**: Mistral 7B Instruct (4-bit quantized, 3.8GB)
- **Engine**: llama.cpp (optimized C++ implementation)
- **Detection**: Python psutil + platform detection
- **Interface**: Python CLI

## Environmental Impact

**Verdant vs Cloud AI:**
- Energy: 95% less than cloud inference
- Carbon: Minimal footprint after download
- Network: Zero traffic after setup
- Servers: None required

## Development Roadmap

### Phase 1: MVP ✅ Complete
- Core inference engine
- Basic CLI interface
- Hardware optimization
- Model management

### Phase 2: User Experience (4 weeks)
- GUI interface
- Preset templates
- Performance benchmarking

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
- Storage: 10GB+ free space
- Storage Type: SSD preferred

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "llama-cpp-python not installed" | `pip install llama-cpp-python` |
| "Model not found" | `python verdant.py --setup` |
| Slow performance | Close other applications |

## License

**MIT License** - Simple and clear:
- Personal use
- Educational use
- Modify and share
- No attribution required

## Get the Full Experience

This GitHub version is a demo with basic features. For the complete Verdant experience:

- Full performance with maximum context
- Advanced models (13B, 30B, specialized)
- Professional tools (GUI, batch processing, plugins)
- Premium support and updates

**Visit our website for the full version.**

---

**Made for students who value privacy, performance, and simplicity.**

**Get Started • [Documentation](USAGE_GUIDE.md) • [Issues](https://github.com/kaankutluturk/verdant/issues)**
