#!/usr/bin/env python3
"""
Launch script for the Tabulator.js collapsible groups frontend.

This runs the new Tabulator frontend alongside your existing app.
"""

import subprocess
import sys
import time
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


def main():
    print("🚀 Launching MonsterC with Tabulator.js Collapsible Groups!")
    print("=" * 60)

    try:
        # Start the Tabulator frontend server
        print("📊 Starting Tabulator.js frontend on http://127.0.0.1:5001...")
        tabulator_process = subprocess.Popen(
            [sys.executable, str(src_path / "tabulator_app.py")], cwd=project_root
        )

        print("✅ Tabulator server started!")
        print("")
        print("🎯 HOW TO USE:")
        print("1. Run your main app: python3 main.py")
        print("2. Upload CSV and click '🤖 Automation High Failures'")
        print("3. Click the '✨ NEW: Collapsible Groups! ✨' link")
        print("4. Enjoy native collapsible test case groups! 🎉")
        print("")
        print("📱 URLs:")
        print("   Main App: http://127.0.0.1:7860")
        print("   Collapsible Groups: http://127.0.0.1:5001")
        print("")
        print("Press Ctrl+C to stop the Tabulator server...")

        # Wait for the process to complete or be interrupted
        tabulator_process.wait()

    except KeyboardInterrupt:
        print("\n🛑 Stopping Tabulator server...")
        tabulator_process.terminate()
        tabulator_process.wait()
        print("✅ Tabulator server stopped!")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
