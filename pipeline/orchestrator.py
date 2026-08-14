"""The pipeline orchestrator.

Runs the five agents in strict order, passing each agent's output to the next.
Each agent's document is persisted to `artifacts/NN_<role>_<name>.md` and becomes
part of the context for the following agent.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.agents import AGENTS, NEXT_AGENT
from pipeline.llm import LLM

log = logging.getLogger("havenhunt.pipeline")

ROOT = Path(__file__).resolve().parent.parent


def build_product_snapshot() -> str:
    """Human-readable inventory of the built product under product/."""
    product_dir = ROOT / "product"
    lines = ["# Product snapshot (product/)", ""]
    for root, _dirs, files in sorted(os.walk(product_dir)):
        rel = Path(root).relative_to(ROOT)
        for fname in sorted(files):
            if fname.endswith((".pyc", ".pyo")) or "__pycache__" in str(rel):
                continue
            p = Path(root) / fname
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            lines.append(f"- `{rel / fname}` ({size:,} B)")
    lines.append("")
    return "\n".join(lines)


def build_code_context(max_chars: int = 60000) -> str:
    """Concatenate the real source so agents can audit the build without inventing.

    Only human-authored implementation files are included (product/, tests/).
    """
    lines = ["# Actual source code of the product (for real review)", ""]
    used = 0
    for base in ("product", "tests"):
        for root, _dirs, files in sorted(os.walk(ROOT / base)):
            rel = Path(root).relative_to(ROOT)
            for fname in sorted(files):
                if not fname.endswith((".py", ".js", ".html", ".css")):
                    continue
                if "__pycache__" in str(rel):
                    continue
                p = Path(root) / fname
                try:
                    body = p.read_text(encoding="utf-8")
                except Exception:  # noqa: BLE001
                    continue
                block = f"\n--- FILE: {rel / fname} ---\n{body}\n"
                if used + len(block) > max_chars:
                    lines.append("\n--- (source truncated for context budget) ---\n")
                    break
                lines.append(block)
                used += len(block)
            else:
                continue
            break
    lines.append("")
    return "\n".join(lines)


def build_agent_context(agent: dict, prior_outputs: dict[str, str]) -> str:
    """Assemble the context block handed to an agent: prior artifacts + org state."""
    ctx: list[str] = [
        "===================================================================",
        "INPUT PACKET FOR THIS AGENT (previous agents' handoffs + org state)",
        "===================================================================",
    ]

    for prev in AGENTS:
        if prev["order"] >= agent["order"]:
            continue
        body = prior_outputs.get(prev["id"], "")
        ctx.append(
            f"\n### Handoff from {prev['role']} ({prev['name']})\n"
            f"Source file: `{prev['output_file']}`\n"
            f"```markdown\n{body[:14000]}\n```"
        )

    ctx.append("\n### Current state of the product code\n")
    ctx.append(build_product_snapshot())

    # The Maker and the Manager must be able to verify claims against real code.
    if agent["id"] in ("maker", "manager"):
        ctx.append(build_code_context())

    ctx.append(
        "\n### Next agent to receive your output\n"
        f"{NEXT_AGENT.get(agent['id'], 'the Founder')}\n"
    )
    return "\n".join(ctx)


class Pipeline:
    def __init__(self, llm: LLM | None = None, workspace: Path | None = None) -> None:
        self.llm = llm or LLM()
        self.workspace = workspace or ROOT
        self.prior_outputs: dict[str, str] = {}
        self.results: dict[str, dict[str, Any]] = {}

    def _save(self, path: str, content: str) -> Path:
        target = (self.workspace / path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def run_agent(self, agent: dict, temperature: float = 0.6) -> dict[str, Any]:
        log.info("Running %s (%s)...", agent["role"], agent["name"])
        context = build_agent_context(agent, self.prior_outputs)
        messages = [
            {"role": "system", "content": agent["system_prompt"]},
            {"role": "user", "content": context},
        ]
        reply = self.llm.chat(messages, temperature=temperature, max_tokens=8000)

        # Maker handoff: its report can carry executable patches. Apply them,
        # verify with the test suite, and append the ground-truth results to the
        # artifact so the Manager audits against reality, not claims.
        if agent["id"] == "maker":
            from pipeline.patcher import execute, render_summary

            summary = execute(reply)
            log.info(
                "  Maker patches: %d requested -> %s",
                summary["patches_requested"],
                ", ".join(f"{r['file']}={r['status']}" for r in summary["results"]) or "none",
            )
            reply = reply.rstrip() + "\n\n" + render_summary(summary)

        artifact_path = self._save(agent["output_file"], reply)
        self.prior_outputs[agent["id"]] = reply

        record = {
            "agent": agent["id"],
            "role": agent["role"],
            "name": agent["name"],
            "artifact": str(artifact_path.relative_to(self.workspace)),
            "chars": len(reply),
        }
        self.results[agent["id"]] = record
        log.info("  -> %s wrote %s (%d chars)", agent["name"], record["artifact"], len(reply))
        return record

    def run(self, temperature: float = 0.6) -> list[dict[str, Any]]:
        """Run all five agents once, in order."""
        records = []
        for agent in AGENTS:
            records.append(self.run_agent(agent, temperature=temperature))
        return records

    def run_cycle(self, cycles: int = 1, temperature: float = 0.6) -> list[list[dict[str, Any]]]:
        """Run the full pipeline `cycles` times. Later cycles inherit context, so the
        Manager's feedback feeds back into the next Researcher run (the loop closes)."""
        all_cycles = []
        for i in range(cycles):
            log.info("=== PIPELINE CYCLE %d/%d ===", i + 1, cycles)
            all_cycles.append(self.run(temperature=temperature))
        return all_cycles
