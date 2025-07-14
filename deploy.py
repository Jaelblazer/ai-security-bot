#!/usr/bin/env python3
"""
Deployment script for AI Security Monitor Bot
Helps set up the bot on various platforms
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def install_dependencies():
    """Install required dependencies"""
    try:
        print("📦 Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("📝 Creating .env file from template...")
        
        # Copy from example
        example_file = Path("env_example.txt")
        if example_file.exists():
            with open(example_file, 'r') as f:
                content = f.read()
            with open(env_file, 'w') as f:
                f.write(content)
            print("✅ .env file created from template")
            print("⚠️  Please edit .env file with your API keys")
        else:
            print("❌ env_example.txt not found")
            return False
    else:
        print("✅ .env file found")
    
    # Check for required variables
    required_vars = ['DISCORD_TOKEN', 'OPENAI_API_KEY']
    missing_vars = []
    
    with open(env_file, 'r') as f:
        content = f.read()
        for var in required_vars:
            if f"{var}=" not in content or f"{var}=your_" in content:
                missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Missing or placeholder values for: {', '.join(missing_vars)}")
        print("Please edit .env file with your actual API keys")
        return False
    
    print("✅ All required environment variables are set")
    return True

def create_dockerfile():
    """Create Dockerfile for containerized deployment"""
    dockerfile_content = """FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "security_bot.py"]
"""
    
    with open("Dockerfile", 'w') as f:
        f.write(dockerfile_content)
    print("✅ Dockerfile created")

def create_railway_config():
    """Create Railway configuration"""
    railway_config = {
        "build": {
            "builder": "nixpacks"
        },
        "deploy": {
            "startCommand": "python security_bot.py",
            "healthcheckPath": "/",
            "healthcheckTimeout": 300,
            "restartPolicyType": "ON_FAILURE"
        }
    }
    
    with open("railway.json", 'w') as f:
        json.dump(railway_config, f, indent=2)
    print("✅ Railway configuration created")

def create_render_config():
    """Create Render configuration"""
    render_config = """services:
  - type: web
    name: ai-security-bot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python security_bot.py
    envVars:
      - key: DISCORD_TOKEN
        sync: false
      - key: OPENAI_API_KEY
        sync: false
"""
    
    with open("render.yaml", 'w') as f:
        f.write(render_config)
    print("✅ Render configuration created")

def test_bot():
    """Test the bot configuration"""
    print("🧪 Testing bot configuration...")
    try:
        # Import and test basic functionality
        from dotenv import load_dotenv
        load_dotenv()
        
        # Check if required modules can be imported
        import discord
        import openai
        import requests
        
        print("✅ All modules imported successfully")
        
        # Check API keys
        discord_token = os.getenv('DISCORD_TOKEN')
        openai_key = os.getenv('OPENAI_API_KEY')
        
        if discord_token and discord_token != 'your_discord_bot_token_here':
            print("✅ Discord token configured")
        else:
            print("⚠️  Discord token not configured")
            
        if openai_key and openai_key != 'your_openai_api_key_here':
            print("✅ OpenAI API key configured")
        else:
            print("⚠️  OpenAI API key not configured")
            
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    """Main deployment function"""
    print("🚀 AI Security Monitor Bot - Deployment Script")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return
    
    # Install dependencies
    if not install_dependencies():
        return
    
    # Check environment file
    if not check_env_file():
        print("\n📝 Next steps:")
        print("1. Edit .env file with your API keys")
        print("2. Run this script again to test")
        return
    
    # Test bot configuration
    if not test_bot():
        return
    
    # Create deployment files
    print("\n📁 Creating deployment files...")
    create_dockerfile()
    create_railway_config()
    create_render_config()
    
    print("\n🎉 Deployment setup complete!")
    print("\n📋 Next steps:")
    print("1. Test locally: python security_bot.py")
    print("2. Deploy to Railway: railway up")
    print("3. Deploy to Render: connect your GitHub repo")
    print("4. Start marketing your bot!")
    
    print("\n💰 Monetization reminder:")
    print("- Target: $40/day = $1,200/month")
    print("- Need: 24-60 Pro users ($20/month) or 6-12 Enterprise clients ($50/month)")
    print("- Focus on getting your first 5 paying clients")

if __name__ == "__main__":
    main() 