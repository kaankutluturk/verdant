# 🌱 EcoAI - Local AI Assistant for Students

> **Eco-friendly, privacy-first AI that runs entirely on your laptop. No cloud, no subscriptions, no data mining.**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Status: MVP](https://img.shields.io/badge/status-MVP-orange.svg)]()

## 🎯 Why EcoAI?

**For Students Who Want:**
- ✅ **Privacy**: Your data never leaves your device
- ✅ **Sustainability**: Minimal energy usage vs cloud AI  
- ✅ **Affordability**: One-time purchase, no monthly fees
- ✅ **Reliability**: Works offline, no internet dependency
- ✅ **Speed**: Optimized for common academic tasks

## ⚡ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Test the installation
python test_ecoai.py

# 3. Setup (downloads model - one time only)
python ecoai.py --setup

# 4. Start using!
python ecoai.py --interactive
```

**First run will download ~4GB model. After that, it's 100% offline.**

## 🚀 Current Features

### ✅ **Working MVP Features**
- **Local Inference**: Mistral 7B Instruct (quantized) running locally
- **Auto Hardware Detection**: Detects RAM, CPU cores, and platform
- **Hardware Optimization**: Automatically configures threads and context based on your system
- **CLI Interface**: Full command-line interface with interactive mode
- **Model Management**: One-time download with validation and progress tracking
- **Cross-platform Support**: Windows, macOS, and Linux

### 🔧 **Hardware Optimization**
- **High Performance**: 16GB+ RAM, 8+ cores → 4096 context, max threads
- **Medium Performance**: 8GB+ RAM, 4+ cores → 2048 context, optimized threads  
- **Low Performance**: <8GB RAM → 1024 context, conservative threads

## 📋 What It Does Best

### Academic Writing Tasks
- **Paraphrasing**: Rewrite text in different styles
- **Proofreading**: Fix grammar, spelling, punctuation
- **Summarization**: Condense long texts
- **Style adjustment**: Formal ↔ casual tone changes

## 💻 System Requirements

| Tier | RAM | CPU | Storage | Speed |
|------|-----|-----|---------|-------|
| **Minimum** | 8GB | 4-core | 5GB | ~3 tok/sec |
| **Recommended** | 16GB | 8-core | 10GB | ~10 tok/sec |

**Supported Platforms:** Windows 10+, macOS 10.15+, Ubuntu 18.04+

## 🧪 Testing

Run the test suite to verify everything works:

```bash
python test_ecoai.py
```

## 📖 Usage Examples

### Interactive Mode
```bash
python ecoai.py --interactive
```

### Single Prompt
```bash
python ecoai.py --prompt "Help me paraphrase this text: The study shows that social media affects students badly."
```

### Setup/Installation
```bash
python ecoai.py --setup
```

## 🔍 Troubleshooting

### Common Issues
1. **"llama-cpp-python not installed"** → Run `pip install llama-cpp-python`
2. **"Model not found"** → Run `python ecoai.py --setup` first
3. **Slow performance** → Check if you meet minimum RAM requirements

### Performance Tips
- Close other applications to free up RAM
- Use SSD storage for faster model loading
- Ensure good ventilation for sustained performance

## 📜 License

**Open Source Core (Apache 2.0 License)**
- ✅ Use for personal and commercial projects
- ✅ Modify and redistribute  
- ✅ Patent protection included

---

**Made with 🌱 for students who care about privacy, sustainability, and affordability.**
