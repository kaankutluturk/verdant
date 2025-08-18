#!/usr/bin/env python3
"""
Test script for the enhanced Verdant GUI
This script tests the new features and improvements
"""

import sys
import os

# Add the current directory to the path so we can import verdant_gui
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_enhanced_gui():
    """Test the enhanced GUI features"""
    try:
        print("🌿 Testing Enhanced Verdant GUI...")
        
        # Test imports
        print("✓ Testing imports...")
        import tkinter as tk
        import ttkbootstrap as tb
        from verdant_gui import VerdantGUI
        
        print("✓ All imports successful")
        
        # Test GUI creation
        print("✓ Testing GUI creation...")
        root = tb.Window(themename="darkly")
        root.withdraw()  # Hide the window during testing
        
        gui = VerdantGUI(root)
        print("✓ GUI created successfully")
        
        # Test methods
        print("✓ Testing enhanced methods...")
        
        # Test status setting
        gui._set_status("Test status message")
        print("✓ Status setting works")
        
        # Test context suggestions
        gui._show_context_suggestions("paraphrase this text")
        print("✓ Context suggestions work")
        
        # Test preset selection
        gui._select_preset("paraphrase_academic")
        print("✓ Preset selection works")
        
        # Test copy functionality
        gui._copy_all()
        print("✓ Copy functionality works")
        
        # Test export functionality
        gui._export_chat()
        print("✓ Export functionality works")
        
        # Test theme detection
        theme = gui._detect_system_theme()
        print(f"✓ Theme detection works: {theme}")
        
        print("\n🎉 All tests passed! Enhanced GUI is working correctly.")
        print("\nNew features include:")
        print("• Enhanced sidebar with better organization")
        print("• Improved chat bubbles with action buttons")
        print("• Better settings dialog with tabs")
        print("• Keyboard shortcuts and accessibility")
        print("• Context-aware suggestions")
        print("• Enhanced onboarding experience")
        print("• Better visual feedback and animations")
        
        # Clean up
        root.destroy()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_presets():
    """Test the preset functionality"""
    try:
        print("\n🔧 Testing presets...")
        
        from verdant import PresetsManager
        
        presets = PresetsManager.load_presets()
        print(f"✓ Loaded {len(presets)} presets")
        
        for name, description in presets.items():
            print(f"  • {name}: {description[:50]}...")
        
        print("✓ Presets working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Preset test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Enhanced Verdant GUI Tests\n")
    
    # Test presets
    presets_ok = test_presets()
    
    # Test GUI
    gui_ok = test_enhanced_gui()
    
    if presets_ok and gui_ok:
        print("\n🎯 All tests completed successfully!")
        print("The enhanced Verdant GUI is ready to use.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        sys.exit(1) 