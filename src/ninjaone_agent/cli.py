"""Interactive command-line entry point."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from .agent import NinjaOneAgent


def _load_environment() -> None:
    # Load only the project .env; never print credentials or overwrite process vars.
    load_dotenv(Path.cwd() / ".env", override=False)


async def _run() -> None:
    _load_environment()
    agent = NinjaOneAgent()
    print("NinjaOne OLMo + LangGraph Agent")
    print("Local model only. Type 'exit' to quit.\n")
    try:
        await agent.start()
        while True:
            try:
                question = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not question:
                continue
            if question.lower() in {"exit", "quit"}:
                break
            try:
                print("\nAssistant:")
                answer = await agent.ask(question)
                print(answer + "\n")
            except Exception as exc:
                print(f"[Agent error] {type(exc).__name__}: {exc}\n")
    finally:
        print("Agent stopped.")


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\nAgent stopped.")


if __name__ == "__main__":
    main()
