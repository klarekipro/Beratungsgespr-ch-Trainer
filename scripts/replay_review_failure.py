#!/usr/bin/env python3
"""Replay a local owner-private review bundle offline; print only a safe outcome."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.dashboard.review_diagnostics import replay
from backend.app.dashboard.review_service import ReviewValidationError
parser=argparse.ArgumentParser();parser.add_argument('bundle',type=Path);args=parser.parse_args()
try:
    replay(args.bundle);print('Validation passed offline. No provider call or persistence.');sys.exit(0)
except ReviewValidationError as exc:
    print('Rejected:',exc.stage,exc.path,exc.reason);sys.exit(1)
except Exception as exc:
    print('Replay failed:',type(exc).__name__);sys.exit(2)
