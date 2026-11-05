#!/usr/bin/env python3
"""Run the local dashboard; optional API key is entered without echo or shell history."""
import argparse
import getpass
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Klare KI local consultation dashboard")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--openai", action="store_true", help="Ask for a server-side API key using hidden input, if absent")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini-2025-04-14"))
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use a port between 1024 and 65535")
    if args.openai and not os.environ.get("OPENAI_API_KEY"):
        if not sys.stdin.isatty():
            parser.error("Use an interactive terminal for hidden key entry, or provide OPENAI_API_KEY through your secret manager.")
        secret = getpass.getpass("OpenAI API key (hidden, kept only for this server process): ").strip()
        if not secret:
            parser.error("No key entered. Run without --openai for scenario mode.")
        os.environ["OPENAI_API_KEY"] = secret
    os.environ["OPENAI_MODEL"] = args.model
    if args.data_dir:
        os.environ["TRAINER_DATA_DIR"] = str(args.data_dir.resolve())
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    import uvicorn
    print(f"Klare KI: http://127.0.0.1:{args.port}")
    print("Local mentor / learner workspaces. This process does not send API requests until an OpenAI dialogue is used.")
    uvicorn.run("backend.app.dashboard.server:app", host="127.0.0.1", port=args.port, access_log=False, workers=1)


if __name__ == "__main__":
    main()
