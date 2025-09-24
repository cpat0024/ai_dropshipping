#!/usr/bin/env python3
"""
AI Supplier Evaluation System - Startup Script
Run this to start the enhanced dropshipping intelligence platform
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    # Set working directory to the aliexpress_scraper folder
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    print("🧠 AI Supplier Evaluation System")
    print("🚀 Starting Dropshipping Intelligence Platform...")
    print("-" * 50)

    # Check if we're in the right directory
    if not Path("src/aliexpress_scraper").exists():
        print("❌ Error: Please run this script from the aliexpress_scraper directory")
        sys.exit(1)

    # Check environment variables
    env_file = Path(".env")
    if env_file.exists():
        print("✅ Environment configuration found")

        # Read and verify key variables
        with open(env_file, "r") as f:
            env_content = f.read()

        if (
            "GOOGLE_API_KEY=" in env_content
            and "AIzaSyBGIulntqZ7CjTPWtgWc2dsmfu55W5i5TI" in env_content
        ):
            print("✅ Gemini AI key configured")
        else:
            print("⚠️  Gemini AI key not found in .env")

        if "SCRAPFLY_KEY=" in env_content:
            print("✅ Scrapfly key configured")
        else:
            print("⚠️  Scrapfly key not found in .env")
    else:
        print("❌ .env file not found - some features may not work")

    print("\n🌐 Starting web server...")
    print("📊 Frontend available at: http://127.0.0.1:8787")
    print("🤖 AI-powered supplier analysis ready")
    print("\n💡 Features available:")
    print("   • Real-time supplier scraping")
    print("   • Gemini AI analysis & insights")
    print("   • Interactive performance charts")
    print("   • Dropshipping risk assessment")
    print("   • Market trend analysis")
    print("\nPress Ctrl+C to stop the server")
    print("-" * 50)

    try:
        # Start the server
        result = subprocess.run(
            [sys.executable, "-m", "aliexpress_scraper.server"], cwd=script_dir
        )
        return result.returncode
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        return 0
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
