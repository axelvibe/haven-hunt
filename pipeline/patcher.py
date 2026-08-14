"""Patch executor — turns the Maker's report into real repository changes.

The Maker is an LLM that cannot touch the filesystem itself, so its report
includes a `## PATCHES` section: a JSON array of precise edits. This executor
applies them safely:

  - `replace`: exact `old` substring must appear exactly once in the target file.
  - `create`: writes a new file (fails if the file already exists).
  - `append`: appends to the end of an existing file.

Safety:
  - original files are backed up before modification
  - every changed Python file is syntax-checked
  - the whole test suite must pass; otherwise all changes are reverted
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger("havenhunt.patcher")

ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT / ".patch_backups"

SAFE_ACTIONS = {"replace", "create", "append"}


# ---------------------------------------------------------------------------
# extraction
# ---------------------------------------------------------------------------
def extract_patches(markdown: str) -> list[dict[str, Any]]:
    """Parse the `## PATCHES` section of the Maker's report into patch dicts."""
    blocks = re.findall(
        r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", markdown
    )
    patches: list[dict[str, Any]] = []
    for raw in blocks:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            for p in data:
                if isinstance(p, dict) and p.get("action") in SAFE_ACTIONS:
                    patches.append(p)
    return patches


# ---------------------------------------------------------------------------
# application
# ---------------------------------------------------------------------------
def _backup(path: Path) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / str(path).replace("/", "_")
    if not target.exists():
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def apply_patch(patch: dict[str, Any]) -> dict[str, str]:
    action = patch["action"]
    rel = patch["file"]
    target = (ROOT / rel).resolve()
    if not str(target).startswith(str(ROOT.resolve())):
        return {"status": "skipped", "reason": f"path outside repo: {rel}"}

    if action == "create":
        if target.exists():
            return {"status": "skipped", "reason": "file already exists"}
        target.parent.mkdir(parents=True, exist_ok=True)
        content = patch.get("content", "")
        target.write_text(content, encoding="utf-8")
        return {"status": "applied", "detail": f"created {rel} ({len(content)} chars)"}

    if not target.exists():
        return {"status": "skipped", "reason": f"file not found: {rel}"}

    _backup(target)
    text = target.read_text(encoding="utf-8")

    if action == "append":
        target.write_text(text + "\n" + patch.get("content", ""), encoding="utf-8")
        return {"status": "applied", "detail": f"appended to {rel}"}

    # replace
    old = patch.get("old")
    new = patch.get("new", "")
    if not old or old not in text:
        return {"status": "skipped", "reason": f"old substring not found in {rel}"}
    if text.count(old) > 1:
        return {"status": "skipped", "reason": f"old substring ambiguous ({text.count(old)} matches) in {rel}"}
    target.write_text(text.replace(old, new, 1), encoding="utf-8")
    return {"status": "applied", "detail": f"replaced in {rel}"}


def _syntax_check(changed: list[Path]) -> bool:
    for p in changed:
        if p.suffix == ".py":
            code = p.read_text(encoding="utf-8")
            try:
                compile(code, str(p), "exec")
            except SyntaxError as exc:
                log.error("Syntax error in %s: %s", p, exc)
                return False
    return True


def run_tests() -> tuple[bool, str]:
    py = sys.executable
    proc = subprocess.run(
        [py, "-m", "pytest", "tests/", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    tail = (proc.stdout or "")[-400:] + (proc.stderr or "")[-200:]
    return proc.returncode == 0, tail


def execute(markdown: str) -> dict[str, Any]:
    """Apply the Maker's patches, verify, revert on failure."""
    patches = extract_patches(markdown)
    results: list[dict[str, Any]] = []
    changed: list[Path] = []

    for patch in patches:
        res = apply_patch(patch)
        results.append({"action": patch.get("action"), "file": patch.get("file"), **res})
        if res["status"] == "applied":
            changed.append((ROOT / patch["file"]).resolve())

    summary = {"patches_requested": len(patches), "results": results, "tests": None}

    if not changed:
        summary["tests"] = {"run": False, "reason": "no patches applied"}
        return summary

    if not _syntax_check(changed):
        _revert(changed)
        summary["tests"] = {"run": False, "reason": "syntax error, reverted"}
        return summary

    ok, tail = run_tests()
    summary["tests"] = {"run": True, "passed": ok, "output_tail": tail.strip()[-300:]}
    if not ok:
        _revert(changed)
        summary["reverted"] = True
    return summary


def _revert(changed: list[Path]) -> None:
    for p in changed:
        backup = BACKUP_DIR / str(p).replace("/", "_")
        if backup.exists():
            p.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
            log.warning("Reverted %s", p)


def render_summary(summary: dict[str, Any]) -> str:
    lines = ["## EXECUTION RESULTS (automated — ground truth)", ""]
    if summary["patches_requested"] == 0:
        lines.append("_No patches were specified in the report._")
        return "\n".join(lines)
    lines.append(f"Patches requested: {summary['patches_requested']}")
    for r in summary["results"]:
        lines.append(
            f"- [{r['status'].upper()}] {r['action']} {r['file']} "
            f"({r.get('detail') or r.get('reason')})"
        )
    t = summary["tests"]
    if t and t.get("run"):
        status = "PASSED" if t["passed"] else "FAILED (changes reverted)"
        lines.append(f"\nTests after patching: **{status}**")
        if t.get("output_tail"):
            lines.append(f"```\n{t['output_tail']}\n```")
    elif t:
        lines.append(f"\nTests: not run — {t.get('reason')}")
    if summary.get("reverted"):
        lines.append("\nAll changes were reverted because the suite failed.")
    return "\n".join(lines)
