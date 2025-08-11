# 📖 Lumina Usage Guide

## 🚀 Quick Start

### **Step 1: Install Dependencies**
```bash
pip install -r requirements.txt
```

### **Step 2: Test Installation**
```bash
python test_lumina.py
```

### **Step 3: Download Model**
```bash
python lumina.py --setup
```

### **Step 4: Start Using**
```bash
python lumina.py --interactive
```

---

## 💻 Command Line Options

### **Setup & Installation**
```bash
# Download and setup the AI model
python lumina.py --setup

# Download specific model
python lumina.py --setup --model mistral-7b-q4
```

### **Interactive Mode**
```bash
# Start interactive chat
python lumina.py --interactive

# Use specific model
python lumina.py --interactive --model mistral-7b-q4
```

### **Single Prompt**
```bash
# Process a single prompt
python lumina.py --prompt "Your question here"

# Use specific model
python lumina.py --prompt "Your question" --model mistral-7b-q4
```

### **Help & Information**
```bash
# Show help
python lumina.py --help

# Show version info
python lumina.py --version
```

---

## 🗣️ Interactive Chat Commands

Once you're in interactive mode, you can use these commands:

| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `clear` | Clear conversation history |
| `quit` | Exit the chat session |
| `exit` | Exit the chat session |
| `bye` | Exit the chat session |

---

## 📝 Usage Examples

### **Academic Writing Help**
```
👤 You: Help me paraphrase this text: "The study shows that social media affects students badly."

🤖 Lumina: Here are some alternative phrasings:
1. "Research indicates that social media negatively impacts student performance."
2. "The research demonstrates adverse effects of social media on students."
3. "Studies reveal that social media has detrimental consequences for students."
```

### **Grammar and Style**
```
👤 You: Fix the grammar in this sentence: "Me and him went to the store."

🤖 Lumina: The correct version is: "He and I went to the store."
```

### **Summarization**
```
👤 You: Summarize this paragraph in 2 sentences: [long paragraph text]

🤖 Lumina: [concise summary in 2 sentences]
```

---

## ⚙️ Performance Optimization

### **Hardware Detection**
Lumina automatically detects your system capabilities:

- **High Performance**: 16GB+ RAM, 8+ cores → 4096 context, max threads
- **Medium Performance**: 8GB+ RAM, 4+ cores → 2048 context, optimized threads  
- **Low Performance**: <8GB RAM → 1024 context, conservative threads

### **Performance Tips**
1. **Close other applications** to free up RAM
2. **Use SSD storage** for faster model loading
3. **Ensure good ventilation** for sustained performance
4. **Monitor system resources** during use

---

## 🔧 Troubleshooting

### **Common Issues**

#### **"llama-cpp-python not installed"**
```bash
pip install llama-cpp-python
```

#### **"Model not found"**
```bash
python lumina.py --setup
```

#### **"Insufficient RAM"**
- Close other applications
- Check if you meet minimum 6GB requirement
- Consider upgrading RAM if possible

#### **Slow Performance**
- Check your performance tier
- Ensure good ventilation
- Close unnecessary applications
- Use SSD storage if available

### **Windows-Specific**
- Run `install_and_test.bat` for easy setup
- Ensure Python is added to PATH during installation
- Run PowerShell as Administrator if needed

---

## 📊 System Requirements

### **Minimum Requirements**
- **RAM**: 8GB (6GB for model + 2GB for system)
- **CPU**: 4 cores
- **Storage**: 5GB free space
- **OS**: Windows 10+, macOS 10.15+, Ubuntu 18.04+

### **Recommended Requirements**
- **RAM**: 16GB+
- **CPU**: 8+ cores
- **Storage**: 10GB+ free space
- **Storage Type**: SSD preferred

---

## 🎯 Best Practices

### **For Students**
1. **Use for brainstorming** - Get ideas for essays and projects
2. **Grammar checking** - Improve writing quality
3. **Style adjustment** - Adapt tone for different audiences
4. **Summarization** - Condense long readings

### **For Academic Writing**
1. **Start with clear prompts** - Be specific about what you need
2. **Use iterative refinement** - Ask follow-up questions
3. **Verify outputs** - Always review AI-generated content
4. **Combine with human creativity** - Use AI as a tool, not replacement

---

## 🔒 Privacy & Security

### **Local Processing**
- ✅ **All data stays on your device**
- ✅ **No internet required after setup**
- ✅ **No data sent to external servers**
- ✅ **Complete privacy control**

### **Model Safety**
- The Mistral 7B model is trained on diverse data
- Use responsibly and ethically
- Verify outputs for academic work
- Follow your institution's AI usage policies

---

## 📚 Advanced Usage

### **Custom Prompts**
Create your own prompt templates:

```bash
python lumina.py --prompt "You are an expert academic writer. Help me improve this paragraph: [your text]"
```

### **Batch Processing**
Process multiple prompts:

```bash
python lumina.py --prompt "First question"
python lumina.py --prompt "Second question"
python lumina.py --prompt "Third question"
```

### **Model Switching**
In the future, you'll be able to switch between different models for different tasks.

---

## 💰 **Get the Full Experience**

**This GitHub version is a demo with basic features. For the complete Lumina experience:**

- 🚀 **Full performance** - Maximum speed and context
- 🧠 **Advanced models** - 13B, 30B, and specialized models
- 🎨 **Professional tools** - GUI, batch processing, plugins
- 📚 **Premium support** - Direct help and updates

**Visit our website for the full version!**

---

## 🆘 Getting Help

### **Documentation**
- `README.md` - Project overview and installation
- `PROJECT_STATUS.md` - Technical implementation details
- `docs/` - Additional documentation

### **Testing**
- `test_lumina.py` - Run tests to verify functionality
- `demo.py` - See features in action

### **Examples**
- `examples/` - Sample usage scenarios

---

## 🎉 You're Ready!

You now have a fully functional local AI assistant that:
- ✅ Runs entirely on your device
- ✅ Respects your privacy
- ✅ Optimizes for your hardware
- ✅ Works offline
- ✅ Provides academic writing help

**Happy learning with Lumina! ✨** 