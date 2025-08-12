# 📖 Verdant Usage Guide

> **Complete guide to using Verdant - the eco-conscious local AI assistant.**

## 🚀 Quick Start

### **Step 1: Install Dependencies**
```bash
pip install -r requirements.txt
```

### **Step 2: Test Installation**
```bash
python test_verdant.py
```

### **Step 3: Setup (Download Model)**
```bash
python verdant.py --setup
```

### **Step 4: Start Chatting**
```bash
python verdant.py --interactive
```

> **💡 Environmental Note**: See [README.md](README.md) for details on Verdant's eco-conscious benefits.

## 📚 **Detailed Usage**

### **Setup Commands**

#### **Basic Setup**
```bash
python verdant.py --setup
```

#### **Setup with Specific Model**
```bash
python verdant.py --setup --model mistral-7b-q4
```

### **Interactive Mode**

#### **Start Interactive Chat**
```bash
python verdant.py --interactive
```

#### **Interactive with Specific Model**
```bash
python verdant.py --interactive --model mistral-7b-q4
```

### **Single Prompt Processing**

#### **Process One Question**
```bash
python verdant.py --prompt "Your question here"
```

#### **Single Prompt with Model**
```bash
python verdant.py --prompt "Your question" --model mistral-7b-q4
```

### **Help and Information**

#### **Show Help**
```bash
python verdant.py --help
```

#### **Show Version**
```bash
python verdant.py --version
```

## 🎯 **Academic Use Cases**

### **1. Paraphrasing Text**
**Input:** "The study shows social media affects students badly"
**Command:** `python verdant.py --prompt "Paraphrase this: The study shows social media affects students badly"`
**Output:** 🤖 Verdant: Here are some alternative phrasings:
- "Research indicates social media platforms have detrimental impacts on student well-being"
- "The research demonstrates that social media negatively influences students"
- "Studies reveal that social media usage adversely affects student outcomes"

### **2. Grammar Correction**
**Input:** "There going to the libary tommorow"
**Command:** `python verdant.py --prompt "Fix the grammar: There going to the libary tommorow"`
**Output:** 🤖 Verdant: The correct version is: "They're going to the library tomorrow."

### **3. Text Summarization**
**Input:** [Long academic text]
**Command:** `python verdant.py --prompt "Summarize this text in 2 sentences: [your text]"`
**Output:** 🤖 Verdant: [concise summary in 2 sentences]

## ⚙️ **Performance Optimization**

### **Automatic Hardware Detection**
Verdant automatically detects your system capabilities:

- **High Performance** (16GB+ RAM, 8+ cores): 4096 context, max threads
- **Medium Performance** (8GB+ RAM, 4+ cores): 2048 context, optimized threads  
- **Low Performance** (<8GB RAM): 1024 context, conservative threads

### **Manual Performance Tuning**
```bash
# High performance mode
python verdant.py --interactive --threads 8 --context 4096

# Conservative mode
python verdant.py --interactive --threads 4 --context 1024
```

## 🔧 **Troubleshooting**

### **Common Issues**

#### **Model Not Found**
```bash
# Download the model first
python verdant.py --setup
```

#### **Slow Performance**
- Close other applications
- Use lower context size: `--context 1024`
- Reduce thread count: `--threads 4`

#### **Memory Issues**
- Ensure you have at least 8GB RAM
- Close unnecessary applications
- Use lower context size

### **Performance Tips**
1. **SSD Storage**: Faster model loading
2. **Dedicated GPU**: Enable GPU acceleration if available
3. **Background Apps**: Close other applications
4. **Model Size**: Start with smaller models if RAM is limited

## 📝 **Advanced Usage**

### **Batch Processing**
```bash
# Process multiple questions
python verdant.py --prompt "First question"
python verdant.py --prompt "Second question"
python verdant.py --prompt "Third question"
```

### **Academic Writing Assistant**
```bash
python verdant.py --prompt "You are an expert academic writer. Help me improve this paragraph: [your text]"
```

### **Custom Prompts**
```bash
python verdant.py --prompt "Act as a math tutor and explain calculus concepts simply"
```

## 🏗️ **Project Structure**

```
verdant/
├── verdant.py              # Main application
├── test_verdant.py         # Test suite
├── demo.py                 # Feature demonstration
├── requirements.txt        # Python dependencies
├── README.md              # Project overview and environmental benefits
├── USAGE_GUIDE.md         # This detailed usage guide
├── PROJECT_STATUS.md      # Development status and roadmap
├── LICENSE                # MIT License
├── .gitignore            # Git ignore rules
├── install_and_test.ps1  # Windows installation
├── install_and_test.bat  # Windows batch file
├── setup_github.ps1      # GitHub setup script
└── setup_github.bat      # GitHub setup batch
```

## 🚀 **Next Steps**

### **After Setup**
1. **Test Installation**: `python test_verdant.py`
2. **Download Model**: `python verdant.py --setup`
3. **Start Chatting**: `python verdant.py --interactive`

### **Explore Features**
- Try different prompt styles
- Test performance with various settings
- Experiment with academic writing tasks

## 💰 **Get the Full Experience**

**This GitHub version is a demo with basic features. For the complete Verdant experience:**

- Full performance with maximum context
- Advanced models (13B, 30B, specialized)
- Professional tools (GUI, batch processing, plugins)
- Premium support and updates

**Visit our website for the full version.**

---

## 📚 **File Descriptions**

- `verdant.py` - Main AI application with CLI interface
- `test_verdant.py` - Run tests to verify functionality
- `demo.py` - Feature demonstration without full model
- `requirements.txt` - Python package dependencies
- `README.md` - Project overview and environmental benefits
- `USAGE_GUIDE.md` - This detailed usage guide
- `PROJECT_STATUS.md` - Development progress and roadmap
- `LICENSE` - MIT License terms
- `install_and_test.ps1` - Windows PowerShell installation
- `install_and_test.bat` - Windows batch installation
- `setup_github.ps1` - GitHub repository setup
- `setup_github.bat` - GitHub setup batch file

## 🎯 **Support**

- **Issues**: Report bugs on GitHub
- **Documentation**: Check this guide and README
- **Community**: Join discussions on GitHub

**Happy learning with Verdant - the AI that cares about our planet! 🌱✨** 