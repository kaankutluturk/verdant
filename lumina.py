#!/usr/bin/env python3
"""
EcoAI MVP - Local AI Assistant for Students 
A lightweight, eco-friendly AI assistant running locally on student laptops. 
 
Copyright 2025 EcoAI Project 
 
Licensed under the Apache License, Version 2.0 (the "License"); 
you may not use this file except in compliance with the License. 
You may obtain a copy of the License at 
 
    http://www.apache.org/licenses/LICENSE-2.0 
 
Unless required by applicable law or agreed to in writing, software 
distributed under the License is distributed on an "AS IS" BASIS, 
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
See the License for the specific language governing permissions and 
limitations under the License. 
"""

import os
import sys
import platform
import subprocess
import hashlib
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
import argparse
import time

# Core configuration
@dataclass
class ModelConfig:
    name: str
    url: str
    filename: str
    checksum: str
    size_mb: int
    min_ram_gb: int

# Model configurations
MODELS = {
    "mistral-7b-q4": ModelConfig(
        name="Mistral 7B Instruct Q4",
        url="https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/mistral-7b-instruct-v0.1.q4_0.gguf",
        filename="mistral-7b-instruct-q4.gguf",
        checksum="",  # We'll calculate this after first download
        size_mb=3800,
        min_ram_gb=6
    )
}

class ModelDownloader:
    """Handle model downloading with progress tracking and validation."""
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
    
    def download_model(self, model_key: str) -> bool:
        """Download a model with progress tracking."""
        if model_key not in MODELS:
            print(f"❌ Unknown model: {model_key}")
            return False
        
        model = MODELS[model_key]
        model_path = self.model_dir / model.filename
        
        # Check if already downloaded
        if model_path.exists():
            print(f"✅ Model already exists: {model_path}")
            return True
        
        print(f"🌐 Downloading {model.name}...")
        print(f"   Size: {model.size_mb} MB")
        print(f"   URL: {model.url}")
        
        try:
            response = requests.get(model.url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Progress bar
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            bar_length = 40
                            filled_length = int(bar_length * downloaded // total_size)
                            bar = '█' * filled_length + '-' * (bar_length - filled_length)
                            print(f"\r   [{bar}] {percent:.1f}% ({downloaded / (1024*1024):.1f} MB)", end='', flush=True)
            
            print(f"\n✅ Download complete: {model_path}")
            
            # Calculate and save checksum
            checksum = self._calculate_checksum(model_path)
            print(f"   Checksum: {checksum}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Download failed: {e}")
            if model_path.exists():
                model_path.unlink()  # Remove partial download
            return False
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def validate_model(self, model_key: str) -> bool:
        """Validate downloaded model file."""
        if model_key not in MODELS:
            return False
        
        model = MODELS[model_key]
        model_path = self.model_dir / model.filename
        
        if not model_path.exists():
            return False
        
        # Check file size
        actual_size = model_path.stat().st_size / (1024 * 1024)  # MB
        if abs(actual_size - model.size_mb) > 50:  # Allow 50MB variance
            print(f"⚠️  File size mismatch: expected {model.size_mb}MB, got {actual_size:.1f}MB")
            return False
        
        print(f"✅ Model validation passed: {model_path}")
        return True
    
    def get_model_path(self, model_key: str) -> Optional[Path]:
        """Get the path to a downloaded model."""
        if model_key not in MODELS:
            return None
        
        model = MODELS[model_key]
        model_path = self.model_dir / model.filename
        
        if not model_path.exists():
            return None
        
        return model_path

class AIInference:
    """Handle AI model inference using llama-cpp-python."""
    
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.llm = None
        self._load_model()
    
    def _load_model(self):
        """Load the model with hardware-optimized settings."""
        try:
            from llama_cpp import Llama
            
            # Get hardware info for optimization
            info = HardwareDetector.get_system_info()
            performance_tier = HardwareDetector.get_performance_tier()
            
            # Configure based on hardware
            if performance_tier == "high":
                n_ctx = 4096
                n_threads = info["cpu_count"]
                n_gpu_layers = 0  # CPU only for now
            elif performance_tier == "medium":
                n_ctx = 2048
                n_threads = max(4, info["cpu_count"] // 2)
                n_gpu_layers = 0
            else:
                n_ctx = 1024
                n_threads = max(2, info["cpu_count"] // 2)
                n_gpu_layers = 0
            
            print(f"🔧 Loading model with {n_threads} threads, context {n_ctx}")
            
            self.llm = Llama(
                model_path=str(self.model_path),
                n_ctx=n_ctx,
                n_threads=n_threads,
                n_gpu_layers=n_gpu_layers,
                verbose=False
            )
            
            print("✅ Model loaded successfully!")
            
        except ImportError:
            print("❌ llama-cpp-python not installed. Run: pip install llama-cpp-python")
            raise
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            raise
    
    def generate_response(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate a response using the loaded model."""
        if not self.llm:
            return "❌ Model not loaded"
        
        try:
            # Format prompt for Mistral Instruct
            formatted_prompt = f"<s>[INST] {prompt} [/INST]"
            
            start_time = time.time()
            
            response = self.llm(
                formatted_prompt,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9,
                stop=["</s>", "[INST]"],
                echo=False
            )
            
            generation_time = time.time() - start_time
            
            # Extract the generated text
            if response and 'choices' in response and len(response['choices']) > 0:
                generated_text = response['choices'][0]['text'].strip()
                
                # Calculate tokens per second
                if 'usage' in response and 'total_tokens' in response['usage']:
                    tokens = response['usage']['total_tokens']
                    tokens_per_sec = tokens / generation_time if generation_time > 0 else 0
                    print(f"⚡ Generated {tokens} tokens in {generation_time:.2f}s ({tokens_per_sec:.1f} tok/s)")
                
                return generated_text
            else:
                return "❌ No response generated"
                
        except Exception as e:
            return f"❌ Generation error: {e}"

class HardwareDetector:
    """Detect system capabilities and recommend optimal settings."""
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get basic system information."""
        try:
            import psutil
            memory_gb = psutil.virtual_memory().total / (1024**3)
        except ImportError:
            memory_gb = 8  # Conservative fallback
        
        return {
            "platform": platform.system(),
            "arch": platform.machine(),
            "cpu_count": os.cpu_count(),
            "memory_gb": memory_gb,
            "python_version": platform.python_version()
        }
    
    @staticmethod
    def get_performance_tier() -> str:
        """Determine performance tier based on hardware."""
        info = HardwareDetector.get_system_info()
        memory_gb = info["memory_gb"]
        cpu_count = info["cpu_count"]
        
        if memory_gb >= 16 and cpu_count >= 8:
            return "high"
        elif memory_gb >= 8 and cpu_count >= 4:
            return "medium"
        else:
            return "low"
    
    @staticmethod
    def check_requirements(model_key: str) -> bool:
        """Check if system meets requirements for a model."""
        if model_key not in MODELS:
            return False
        
        model = MODELS[model_key]
        info = HardwareDetector.get_system_info()
        
        if info["memory_gb"] < model.min_ram_gb:
            print(f"❌ Insufficient RAM: {info['memory_gb']:.1f}GB < {model.min_ram_gb}GB required")
            return False
        
        print(f"✅ System requirements met:")
        print(f"   RAM: {info['memory_gb']:.1f}GB (required: {model.min_ram_gb}GB)")
        print(f"   CPU: {info['cpu_count']} cores")
        print(f"   Platform: {info['platform']} {info['arch']}")
        return True

class InteractiveChat:
    """Handle interactive chat interface."""
    
    def __init__(self, ai_inference: AIInference):
        self.ai = ai_inference
        self.conversation_history = []
    
    def start_chat(self):
        """Start interactive chat session."""
        print("\n💬 EcoAI Interactive Chat")
        print("=" * 50)
        print("Type 'quit', 'exit', or 'bye' to end the session")
        print("Type 'clear' to clear conversation history")
        print("Type 'help' for available commands")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("👋 Goodbye! Thanks for using EcoAI.")
                    break
                
                if user_input.lower() == 'clear':
                    self.conversation_history.clear()
                    print("🧹 Conversation history cleared")
                    continue
                
                if user_input.lower() == 'help':
                    self._show_help()
                    continue
                
                # Generate response
                print("\n🤖 EcoAI: ", end='', flush=True)
                response = self.ai.generate_response(user_input)
                print(response)
                
                # Store in history
                self.conversation_history.append({
                    'user': user_input,
                    'assistant': response,
                    'timestamp': time.time()
                })
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! Thanks for using EcoAI.")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    def _show_help(self):
        """Show available commands."""
        print("\n📚 Available Commands:")
        print("  help     - Show this help message")
        print("  clear    - Clear conversation history")
        print("  quit     - Exit the chat session")
        print("  exit     - Exit the chat session")
        print("  bye      - Exit the chat session")

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="EcoAI - Local AI Assistant")
    parser.add_argument("--setup", action="store_true", help="Run initial setup")
    parser.add_argument("--prompt", type=str, help="Single prompt to process")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--model", type=str, default="mistral-7b-q4", help="Model to use")
    
    args = parser.parse_args()
    
    if args.setup:
        print("🌱 EcoAI Setup")
        print("=" * 50)
        
        # Check system requirements
        if not HardwareDetector.check_requirements(args.model):
            print("\n❌ Setup failed: System requirements not met")
            return
        
        # Download model
        downloader = ModelDownloader()
        if not downloader.download_model(args.model):
            print("\n❌ Setup failed: Model download failed")
            return
        
        # Validate model
        if not downloader.validate_model(args.model):
            print("\n❌ Setup failed: Model validation failed")
            return
        
        print("\n🎉 Setup complete! You can now run:")
        print("   python ecoai.py --interactive")
        return
    
    if args.interactive:
        print("🚀 Starting EcoAI Interactive Mode...")
        
        # Check if model exists
        downloader = ModelDownloader()
        model_path = downloader.get_model_path(args.model)
        
        if not model_path:
            print(f"❌ Model not found. Please run setup first:")
            print(f"   python ecoai.py --setup")
            return
        
        try:
            # Load AI model
            ai = AIInference(model_path)
            
            # Start interactive chat
            chat = InteractiveChat(ai)
            chat.start_chat()
            
        except Exception as e:
            print(f"❌ Failed to start interactive mode: {e}")
            print("Please ensure llama-cpp-python is installed:")
            print("   pip install llama-cpp-python")
        return
    
    if args.prompt:
        print("💬 Processing prompt...")
        
        # Check if model exists
        downloader = ModelDownloader()
        model_path = downloader.get_model_path(args.model)
        
        if not model_path:
            print(f"❌ Model not found. Please run setup first:")
            print(f"   python ecoai.py --setup")
            return
        
        try:
            # Load AI model
            ai = AIInference(model_path)
            
            # Generate response
            response = ai.generate_response(args.prompt)
            print(f"\n🤖 EcoAI: {response}")
            
        except Exception as e:
            print(f"❌ Failed to process prompt: {e}")
            print("Please ensure llama-cpp-python is installed:")
            print("   pip install llama-cpp-python")
        return
    
    print("EcoAI MVP - Run with --setup first, then --interactive")

if __name__ == "__main__":
    main()
