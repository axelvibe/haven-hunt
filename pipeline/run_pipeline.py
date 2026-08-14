"""Run the HavenHunt agentic pipeline.

Usage:
    uv run python -m pipeline.run_pipeline [--cycles N] [--temperature F]
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from pipeline.llm import LLM  # noqa: E402
from pipeline.orchestrator import Pipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the five-agent HavenHunt pipeline.")
    parser.add_argument("--cycles", type=int, default=1, help="Pipeline cycles (default 1)")
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    )

    pipeline = Pipeline(llm=LLM())
    pipeline.run_cycle(cycles=args.cycles, temperature=args.temperature)

    llm = pipeline.llm
    print("\n===== PIPELINE COMPLETE =====")
    for rec in pipeline.results.values():
        print(f"  [{rec['role']:13s}] {rec['name']:8s} -> {rec['artifact']} ({rec['chars']:,} chars)")
    print(f"\n{llm.token_budget()}")


if __name__ == "__main__":
    main()
