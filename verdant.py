#!/usr/bin/env python3
"""
Verdant - Local AI Assistant for Students 
A lightweight, eco-friendly AI assistant running locally on student laptops. 
 
Copyright 2025 Verdant Project 
 
Licensed under the MIT License (the "License"); 
you may not use this file except in compliance with the License. 
You may obtain a copy of the License at 
 
    https://opensource.org/licenses/MIT
 
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
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import argparse
import time
import json

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

PREFERENCES_DIR = Path.home() / ".verdant"
PREFERENCES_FILE = PREFERENCES_DIR / "config.json"
PRESETS_FILE = Path(__file__).parent / "presets.json"

class UserPreferences:
    """Load and save user preferences for Verdant."""

    DEFAULTS = {
        "model": "mistral-7b-q4",
        "threads": None,       # auto
        "context": None,       # auto
        "temperature": 0.7,
        "top_p": 0.9,
    }

    @staticmethod
    def load(path: Optional[Path] = None) -> Dict[str, Any]:
        prefs_path = path or PREFERENCES_FILE
        try:
            if prefs_path.exists():
                with open(prefs_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Merge with defaults
                merged = dict(UserPreferences.DEFAULTS)
                merged.update({k: v for k, v in data.items() if v is not None})
                return merged
        except Exception:
            pass
        return dict(UserPreferences.DEFAULTS)

    @staticmethod
    def save(prefs: Dict[str, Any], path: Optional[Path] = None) -> None:
        prefs_path = path or PREFERENCES_FILE
        prefs_path.parent.mkdir(parents=True, exist_ok=True)
        with open(prefs_path, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)

class PresetsManager:
    """Manage prompt presets from presets.json."""

    @staticmethod
    def load_presets() -> Dict[str, str]:
        try:
            if PRESETS_FILE.exists():
                with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return {k: str(v) for k, v in data.items()}
        except Exception:
            pass
        return {}

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
    
    def __init__(self, model_path: Path, n_ctx: Optional[int] = None, n_threads: Optional[int] = None,
                 temperature: float = 0.7, top_p: float = 0.9):
        self.model_path = model_path
        self.llm = None
        self.n_ctx_override = n_ctx
        self.n_threads_override = n_threads
        self.temperature = temperature
        self.top_p = top_p
        self._load_model()
    
    def _load_model(self):
        """Load the model with hardware-optimized settings."""
        try:
            from llama_cpp import Llama
            
            # Get hardware info for optimization
            info = HardwareDetector.get_system_info()
            performance_tier = HardwareDetector.get_performance_tier()
            
            # Configure based on hardware or overrides
            if performance_tier == "high":
                default_n_ctx = 4096
                default_threads = info["cpu_count"]
            elif performance_tier == "medium":
                default_n_ctx = 2048
                default_threads = max(4, info["cpu_count"] // 2)
            else:
                default_n_ctx = 1024
                default_threads = max(2, info["cpu_count"] // 2)

            n_ctx = self.n_ctx_override or default_n_ctx
            n_threads = self.n_threads_override or default_threads
            n_gpu_layers = 0  # CPU only for now
            
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
                temperature=self.temperature,
                top_p=self.top_p,
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
        self.conversation_history: List[Dict[str, Any]] = []
    
    def start_chat(self):
        """Start interactive chat session."""
        print("\n💬 Verdant Interactive Chat")
        print("=" * 50)
        print("Type 'quit', 'exit', or 'bye' to end the session")
        print("Type 'clear' to clear conversation history")
        print("Type 'save <file.json>' to save session history")
        print("Type 'load <file.json>' to load a session history")
        print("Type 'help' for available commands")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                
                lower = user_input.lower()
                if lower in ['quit', 'exit', 'bye']:
                    print("👋 Goodbye! Thanks for using Verdant.")
                    break
                
                if lower == 'clear':
                    self.conversation_history.clear()
                    print("🧹 Conversation history cleared")
                    continue
                
                if lower == 'help':
                    self._show_help()
                    continue
                
                if lower.startswith('save '):
                    path = user_input.split(' ', 1)[1].strip()
                    self.save_history(Path(path))
                    print(f"💾 Saved conversation to {path}")
                    continue
                
                if lower.startswith('load '):
                    path = user_input.split(' ', 1)[1].strip()
                    self.load_history(Path(path))
                    print(f"📥 Loaded conversation from {path}")
                    continue
                
                # Generate response
                print("\n🤖 Verdant: ", end='', flush=True)
                response = self.ai.generate_response(user_input)
                print(response)
                
                # Store in history
                self.conversation_history.append({
                    'user': user_input,
                    'assistant': response,
                    'timestamp': time.time()
                })
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! Thanks for using Verdant.")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    def _show_help(self):
        """Show available commands."""
        print("\n📚 Available Commands:")
        print("  help              - Show this help message")
        print("  clear             - Clear conversation history")
        print("  save <file.json>  - Save conversation history to a file")
        print("  load <file.json>  - Load conversation history from a file")
        print("  quit/exit/bye     - Exit the chat session")
    
    def save_history(self, file_path: Path):
        data = {
            'history': self.conversation_history,
            'saved_at': time.time(),
            'version': '1.0'
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def load_history(self, file_path: Path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.conversation_history = data.get('history', [])


def run_benchmark(ai: AIInference, runs: int = 1) -> None:
    """Run a basic generation benchmark and print throughput."""
    test_prompt = "Explain why local AI can be more eco‑friendly than cloud AI in 3 bullet points."
    total_tokens = 0
    total_time = 0.0
    for i in range(runs):
        start = time.time()
        out = ai.generate_response(test_prompt, max_tokens=256)
        elapsed = time.time() - start
        total_time += elapsed
        # Fallback token estimate if usage not provided
        tokens = max(1, len(out.split()))
        total_tokens += tokens
        print(f"Run {i+1}: {tokens} est. tokens in {elapsed:.2f}s")
    avg_tps = total_tokens / total_time if total_time > 0 else 0
    print(f"\n📊 Benchmark: {total_tokens} est. tokens over {runs} run(s) in {total_time:.2f}s → {avg_tps:.1f} tok/s (approx)")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Verdant - Local AI Assistant")
    parser.add_argument("--setup", action="store_true", help="Run initial setup")
    parser.add_argument("--prompt", type=str, help="Single prompt to process")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--model", type=str, help="Model to use")

    # Phase 2: advanced controls
    parser.add_argument("--threads", type=int, help="Override number of CPU threads")
    parser.add_argument("--context", type=int, help="Override context window size")
    parser.add_argument("--temperature", type=float, help="Sampling temperature (default from prefs)")
    parser.add_argument("--top_p", type=float, help="Top-p nucleus sampling (default from prefs)")

    # Presets
    parser.add_argument("--preset", type=str, help="Use a prompt preset by name (presets.json)")
    parser.add_argument("--list-presets", action="store_true", help="List available presets")

    # Preferences
    parser.add_argument("--use-prefs", action="store_true", help="Load and apply saved user preferences")
    parser.add_argument("--save-prefs", action="store_true", help="Save the current settings to preferences")
    parser.add_argument("--prefs-path", type=str, help="Custom path to preferences JSON")

    # Sessions
    parser.add_argument("--load-session", type=str, help="Load a conversation session JSON before starting")
    parser.add_argument("--save-session", type=str, help="Save conversation session JSON after finishing")

    # Benchmark
    parser.add_argument("--benchmark", action="store_true", help="Run a simple generation benchmark and exit")
    parser.add_argument("--benchmark-runs", type=int, default=1, help="Number of benchmark runs")

    args = parser.parse_args()

    # Load preferences
    prefs_path = Path(args.prefs_path) if args.prefs_path else None
    prefs = UserPreferences.load(prefs_path) if args.use_prefs else UserPreferences.DEFAULTS.copy()

    # Apply CLI overrides
    model_key = args.model or prefs.get("model") or "mistral-7b-q4"
    threads = args.threads if args.threads is not None else prefs.get("threads")
    context = args.context if args.context is not None else prefs.get("context")
    temperature = args.temperature if args.temperature is not None else prefs.get("temperature", 0.7)
    top_p = args.top_p if args.top_p is not None else prefs.get("top_p", 0.9)

    if args.save_prefs:
        new_prefs = {
            "model": model_key,
            "threads": threads,
            "context": context,
            "temperature": temperature,
            "top_p": top_p,
        }
        UserPreferences.save(new_prefs, prefs_path)
        print(f"💾 Preferences saved to {prefs_path or PREFERENCES_FILE}")

    # Setup path
    if args.setup:
        print("🌱 Verdant Setup")
        print("=" * 50)
        
        # Check system requirements
        if not HardwareDetector.check_requirements(model_key):
            print("\n❌ Setup failed: System requirements not met")
            return
        
        # Download model
        downloader = ModelDownloader()
        if not downloader.download_model(model_key):
            print("\n❌ Setup failed: Model download failed")
            return
        
        # Validate model
        if not downloader.validate_model(model_key):
            print("\n❌ Setup failed: Model validation failed")
            return
        
        print("\n🎉 Setup complete! You can now run:")
        print("   python verdant.py --interactive")
        return

    # List presets if requested
    if args.list_presets:
        presets = PresetsManager.load_presets()
        if not presets:
            print("(no presets found)")
        else:
            print("Available presets:")
            for name in sorted(presets.keys()):
                print(f"  - {name}")
        return

    # Ensure model is available if any action requires it
    if args.interactive or args.prompt or args.benchmark:
        downloader = ModelDownloader()
        model_path = downloader.get_model_path(model_key)
        if not model_path:
            print(f"❌ Model not found. Please run setup first:")
            print(f"   python verdant.py --setup --model {model_key}")
            return

        try:
            # Load AI model
            ai = AIInference(model_path, n_ctx=context, n_threads=threads, temperature=temperature, top_p=top_p)
        except Exception as e:
            print(f"❌ Failed to initialize model: {e}")
            print("Please ensure llama-cpp-python is installed:")
            print("   pip install llama-cpp-python")
            return

        # Benchmark mode
        if args.benchmark:
            print("🚀 Running benchmark...")
            run_benchmark(ai, runs=args.benchmark_runs)
            return

        # Interactive mode
        if args.interactive:
            print("🚀 Starting Verdant Interactive Mode...")
            chat = InteractiveChat(ai)
            # Load session if provided
            if args.load_session:
                try:
                    chat.load_history(Path(args.load_session))
                    print(f"📥 Loaded session from {args.load_session}")
                except Exception as e:
                    print(f"⚠️  Failed to load session: {e}")
            
            chat.start_chat()

            # Save session if requested
            if args.save_session:
                try:
                    chat.save_history(Path(args.save_session))
                    print(f"💾 Saved session to {args.save_session}")
                except Exception as e:
                    print(f"⚠️  Failed to save session: {e}")
            return

        # Single prompt
        if args.prompt:
            # Apply preset if any
            final_prompt = args.prompt
            if args.preset:
                presets = PresetsManager.load_presets()
                preset = presets.get(args.preset)
                if not preset:
                    print(f"⚠️  Preset '{args.preset}' not found; proceeding without it")
                else:
                    final_prompt = f"{preset}\n\nUser prompt: {args.prompt}"

            print("💬 Processing prompt...")
            try:
                response = ai.generate_response(final_prompt)
                print(f"\n🤖 Verdant: {response}")
            except Exception as e:
                print(f"❌ Failed to process prompt: {e}")
                print("Please ensure llama-cpp-python is installed:")
                print("   pip install llama-cpp-python")
            return

    print("Verdant MVP - Run with --setup first, then --interactive")

if __name__ == "__main__":
    main()
