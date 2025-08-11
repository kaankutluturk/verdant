#!/usr/bin/env python3
"""
Test script for EcoAI MVP functionality.
Run this to verify the implementation works correctly.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ecoai import HardwareDetector, ModelDownloader

def test_hardware_detection():
    """Test hardware detection functionality."""
    print("🧪 Testing Hardware Detection...")
    
    try:
        info = HardwareDetector.get_system_info()
        print(f"✅ System info: {info}")
        
        tier = HardwareDetector.get_performance_tier()
        print(f"✅ Performance tier: {tier}")
        
        return True
    except Exception as e:
        print(f"❌ Hardware detection failed: {e}")
        return False

def test_model_downloader():
    """Test model downloader functionality."""
    print("\n🧪 Testing Model Downloader...")
    
    try:
        downloader = ModelDownloader()
        print(f"✅ Model downloader initialized: {downloader.model_dir}")
        
        # Test validation without model
        is_valid = downloader.validate_model("mistral-7b-q4")
        print(f"✅ Model validation test: {is_valid}")
        
        return True
    except Exception as e:
        print(f"❌ Model downloader test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 EcoAI MVP Test Suite")
    print("=" * 40)
    
    tests = [
        test_hardware_detection,
        test_model_downloader,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! EcoAI is ready to use.")
        print("\nNext steps:")
        print("1. Run: python ecoai.py --setup")
        print("2. Run: python ecoai.py --interactive")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 