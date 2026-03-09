#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    print("🔍 Checking Python version...")
    required_version = (3, 9)
    if sys.version_info < required_version:
        print(f"❌ Python {required_version[0]}.{required_version[1]}+ is required. Found {sys.version_info.major}.{sys.version_info.minor}.")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected.")
    return True

def check_env_vars():
    print("\n🔍 Checking environment variables (.env)...")
    if not Path(".env").exists():
        print("❌ .env file not found. Please copy .env.example to .env and fill in your keys.")
        return False
    
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "NVIDIA_API_KEY"]
    all_found = True
    for key in keys:
        if os.getenv(key):
            print(f"✅ {key} found.")
        else:
            print(f"⚠️ {key} missing (some models will not work).")
            # We don't return False here as you might only need one provider
    return True

def check_dependencies():
    print("\n🔍 Checking installed dependencies...")
    try:
        import openai
        import anthropic
        import pandas
        import httpx
        print("✅ Core dependencies (openai, anthropic, pandas, httpx) found.")
    except ImportError as e:
        print(f"❌ Missing dependency: {e.name}. Run 'pip install -r requirements.txt'.")
        return False
    return True

def check_k8s():
    print("\n🔍 Checking Kubernetes connectivity (optional)...")
    try:
        res = subprocess.run(["kubectl", "cluster-info"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            print("✅ kubectl connected to cluster.")
        else:
            print("⚠️ kubectl not connected to a cluster. Chaos tasks will fail.")
    except FileNotFoundError:
        print("⚠️ kubectl not found. Infrastructure tasks will fail.")
    return True

def main():
    print("==============================================")
    print("  k8s-llm-rca-bench: Environment Doctor  ")
    print("==============================================\n")
    
    success = True
    success &= check_python_version()
    success &= check_dependencies()
    success &= check_env_vars()
    check_k8s()
    
    print("\n--- Summary ---")
    if success:
        print("🚀 Environment looks good! You are ready to benchmark.")
    else:
        print("🔧 Please fix the issues above before running.")
        sys.exit(1)

if __name__ == "__main__":
    main()
