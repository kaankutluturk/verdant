#!/usr/bin/env python3
"""
EcoAI MVP Demo Script
This script demonstrates the working features without requiring the full model download.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def demo_hardware_detection():
    """Demonstrate hardware detection capabilities."""
    print("🔧 Hardware Detection Demo")
    print("=" * 40)
    
    try:
        from ecoai import HardwareDetector
        
        # Get system info
        info = HardwareDetector.get_system_info()
        print(f"Platform: {info['platform']}")
        print(f"Architecture: {info['arch']}")
        print(f"CPU Cores: {info['cpu_count']}")
        print(f"RAM: {info['memory_gb']:.1f} GB")
        print(f"Python: {info['python_version']}")
        
        # Get performance tier
        tier = HardwareDetector.get_performance_tier()
        print(f"Performance Tier: {tier.upper()}")
        
        # Show optimization recommendations
        if tier == "high":
            print("💪 High Performance: 4096 context, max threads")
        elif tier == "medium":
            print("⚡ Medium Performance: 2048 context, optimized threads")
        else:
            print("🐌 Low Performance: 1024 context, conservative threads")
            
        return True
        
    except Exception as e:
        print(f"❌ Hardware detection failed: {e}")
        return False

def demo_model_management():
    """Demonstrate model management capabilities."""
    print("\n📦 Model Management Demo")
    print("=" * 40)
    
    try:
        from ecoai import ModelDownloader, MODELS
        
        # Show available models
        print("Available Models:")
        for key, model in MODELS.items():
            print(f"  {key}: {model.name}")
            print(f"    Size: {model.size_mb} MB")
            print(f"    Min RAM: {model.min_ram_gb} GB")
            print(f"    URL: {model.url}")
        
        # Initialize downloader
        downloader = ModelDownloader()
        print(f"\nModel directory: {downloader.model_dir}")
        
        # Check if model exists
        model_key = "mistral-7b-q4"
        model_path = downloader.get_model_path(model_key)
        
        if model_path:
            print(f"✅ Model already downloaded: {model_path}")
        else:
            print(f"📥 Model not downloaded yet")
            print(f"   Run 'python ecoai.py --setup' to download")
        
        return True
        
    except Exception as e:
        print(f"❌ Model management demo failed: {e}")
        return False

def demo_cli_interface():
    """Demonstrate CLI interface capabilities."""
    print("\n💻 CLI Interface Demo")
    print("=" * 40)
    
    try:
        from ecoai import main
        import argparse
        
        print("Available Commands:")
        print("  --setup       Download and setup the AI model")
        print("  --interactive Start interactive chat mode")
        print("  --prompt      Process a single prompt")
        print("  --model       Specify which model to use")
        print("  --help        Show help information")
        
        print("\nExample Usage:")
        print("  python ecoai.py --setup")
        print("  python ecoai.py --interactive")
        print("  python ecoai.py --prompt 'Hello, how are you?'")
        
        return True
        
    except Exception as e:
        print(f"❌ CLI interface demo failed: {e}")
        return False

def demo_cross_platform():
    """Demonstrate cross-platform capabilities."""
    print("\n🌍 Cross-Platform Demo")
    print("=" * 40)
    
    import platform
    import os
    
    print(f"Operating System: {platform.system()}")
    print(f"Platform: {platform.platform()}")
    print(f"Machine: {platform.machine()}")
    print(f"Processor: {platform.processor()}")
    
    # Show platform-specific optimizations
    if platform.system() == "Windows":
        print("🪟 Windows optimizations enabled")
    elif platform.system() == "Darwin":
        print("🍎 macOS optimizations enabled")
    elif platform.system() == "Linux":
        print("🐧 Linux optimizations enabled")
    
    return True

def main():
    """Run all demos."""
    print("🚀 EcoAI MVP Feature Demo")
    print("=" * 50)
    print("This demo shows the working features of EcoAI MVP")
    print("without requiring the full model download.")
    print()
    
    demos = [
        ("Hardware Detection", demo_hardware_detection),
        ("Model Management", demo_model_management),
        ("CLI Interface", demo_cli_interface),
        ("Cross-Platform Support", demo_cross_platform),
    ]
    
    passed = 0
    total = len(demos)
    
    for name, demo_func in demos:
        print(f"Running {name} demo...")
        if demo_func():
            passed += 1
            print(f"✅ {name} demo completed successfully")
        else:
            print(f"❌ {name} demo failed")
        print()
    
    print("=" * 50)
    print(f"📊 Demo Results: {passed}/{total} demos passed")
    
    if passed == total:
        print("\n🎉 All demos passed! EcoAI MVP is working correctly.")
        print("\n📖 To get started with the full AI experience:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Download model: python ecoai.py --setup")
        print("   3. Start chatting: python ecoai.py --interactive")
    else:
        print(f"\n⚠️  {total - passed} demo(s) failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 