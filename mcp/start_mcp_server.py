#!/usr/bin/env python3
"""
Startup script for the MCP Flood Alert Server
This script provides easy commands to start different components of the system.
"""

import asyncio
import sys
import subprocess
from pathlib import Path

def print_banner():
    """Print the system banner"""
    print("🚨 AI-Driven Natural Disaster Alert System")
    print("=" * 50)
    print("MCP Backend Server")
    print("=" * 50)

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import mcp
        import boto3
        import requests
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_env_file():
    """Check if .env file exists"""
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file found")
        return True
    else:
        print("❌ .env file not found")
        print("Please create a .env file with your API keys:")
        print("TWITTER_BEARER_TOKEN=your_token")
        print("AWS_ACCESS_KEY=your_key")
        print("AWS_SECRET_ACCESS_KEY=your_secret")
        print("WEATHER_LOCATION_KB_ID=your_kb_id")
        return False

def run_mcp_server():
    """Run the MCP server"""
    print("\n🚀 Starting MCP Server...")
    try:
        subprocess.run([sys.executable, "mcp_server.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start MCP server: {e}")
    except KeyboardInterrupt:
        print("\n🛑 MCP server stopped")

def run_demo():
    """Run the complete system demo"""
    print("\n🎬 Running System Demo...")
    try:
        subprocess.run([sys.executable, "flood_alert_orchestrator.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Demo failed: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Demo stopped")

def run_tests():
    """Run the test suite"""
    print("\n🧪 Running Test Suite...")
    try:
        subprocess.run([sys.executable, "test_mcp_server.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Tests stopped")

def show_menu():
    """Show the main menu"""
    print("\n📋 Available Commands:")
    print("1. Start MCP Server")
    print("2. Run System Demo")
    print("3. Run Test Suite")
    print("4. Check System Status")
    print("5. Exit")
    print()

def check_system_status():
    """Check the overall system status"""
    print("\n🔍 System Status Check:")
    print("-" * 30)
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check environment
    env_ok = check_env_file()
    
    # Check key files
    files_to_check = [
        "mcp_server.py",
        "flood_alert_orchestrator.py", 
        "test_mcp_server.py",
        "check_user_input.py",
        "tweet.py",
        "weather.py",
        "config_setting.py"
    ]
    
    files_ok = True
    for file in files_to_check:
        if Path(file).exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - Missing")
            files_ok = False
    
    print("\n📊 Overall Status:")
    if deps_ok and env_ok and files_ok:
        print("✅ System ready to run")
    else:
        print("❌ System needs attention")
        if not deps_ok:
            print("   - Install missing dependencies")
        if not env_ok:
            print("   - Create .env file")
        if not files_ok:
            print("   - Check file structure")

def main():
    """Main function"""
    print_banner()
    
    while True:
        show_menu()
        try:
            choice = input("Enter your choice (1-5): ").strip()
            
            if choice == "1":
                if check_dependencies() and check_env_file():
                    run_mcp_server()
                else:
                    print("❌ Please fix the issues above before starting the server")
            
            elif choice == "2":
                if check_dependencies() and check_env_file():
                    run_demo()
                else:
                    print("❌ Please fix the issues above before running the demo")
            
            elif choice == "3":
                if check_dependencies():
                    run_tests()
                else:
                    print("❌ Please install dependencies before running tests")
            
            elif choice == "4":
                check_system_status()
            
            elif choice == "5":
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice. Please enter 1-5.")
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
