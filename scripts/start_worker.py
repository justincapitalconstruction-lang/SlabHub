#!/usr/bin/env python
"""
SlabHub Worker Startup Script

Convenience script to start a SlabHub background worker.

Usage:
    python scripts/start_worker.py
    python scripts/start_worker.py --type gpt --queues gpt,analysis
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.app.worker import main

if __name__ == "__main__":
    main()
