#!/usr/bin/env python3
"""
eval/rescore.py — Retroactive metric rescorer.

For rows in incidents.csv that are missing log_faithfulness, cmd_executability,
or confidence_score, this script recomputes them from:
  - The evidence_cited field reconstructed from the root_cause_description
    (best effort) OR from re-parsing the raw log files on disk

Since old rows do NOT have evidence_cited stored in the CSV, we cannot
retroactively compute log_faithfulness for them without re-calling the LLM.

Instead, this script:
1. For rows with EMPTY log_faithfulness → calls score_log_faithfulness using
   the root_cause_description as a proxy evidence list (each sentence
   is treated as a claim and checked against raw logs)
2. For rows with EMPTY cmd_executability → re-extracts kubectl-looking commands
   from root_cause_description and dry-runs them
3. Rewrites the CSV with all columns filled

This is a CONSERVATIVE estimate — the real faithfulness scores will be
computed on new runs where evidence_cited is stored properly.
"""
import csv
import json
import re
import subprocess
from pathlib import Path
from eval.evaluate import score_command_executability, score_log_faithfulness

CSV_PATH = Path("data/incidents.csv")
LOGS_ROOT = Path("data/raw_logs")

FIELDNAMES = [
    "incident_id", "model", "latency_sec", "rca_accuracy",
    "hallucination_penalty", "log_faithfulness", "cmd_executability",
    "remediation_safe", "confidence_score", "root_cause_description"
]


def load_raw_logs(incident_id: str) -> dict:
    """Load all raw text files for an incident into a dict."""
    inc_dir = LOGS_ROOT / incident_id
    result = {}
    for fname in ("pod_logs.txt", "describe_output.txt", "events.txt"):
        p = inc_dir / fname
        if p.exists():
            result[fname] = p.read_text()
    return result


def extract_sentence_claims(text: str) -> list[str]:
    """
    Split root_cause_description into sentence-level claims to use
    as a proxy for evidence_cited in old rows.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    # Filter to substantive sentences (>30 chars, not generic)
    return [s for s in sentences if len(s) > 30]


def extract_kubectl_commands(text: str) -> list[str]:
    """Pull any kubectl-looking strings from freeform text."""
    return re.findall(r'kubectl\s+\S+[^\n,;]*', text)


def rescore_row(row: dict) -> dict:
    """Fill in missing metric columns for a single CSV row."""
    updated = dict(row)
    inc_id = row["incident_id"]
    raw_logs = load_raw_logs(inc_id)

    # ── log_faithfulness ────────────────────────────────────────────────────
    if not row.get("log_faithfulness") and raw_logs:
        claims = extract_sentence_claims(row.get("root_cause_description", ""))
        if claims:
            faith = score_log_faithfulness(claims, raw_logs)
        else:
            faith = 0.0
        updated["log_faithfulness"] = round(faith, 3)

    # ── cmd_executability ───────────────────────────────────────────────────
    if not row.get("cmd_executability"):
        cmds = extract_kubectl_commands(row.get("root_cause_description", ""))
        if cmds:
            exec_score = score_command_executability(cmds)
        else:
            exec_score = 0.0
        updated["cmd_executability"] = round(exec_score, 3)

    # ── confidence_score — we have no record of the original value ──────────
    # Leave blank; new runs will populate it.

    return updated


if __name__ == "__main__":
    rows = list(csv.DictReader(CSV_PATH.open()))
    rescored = []
    n_updated = 0

    for row in rows:
        needs_update = (
            not row.get("log_faithfulness") or
            not row.get("cmd_executability")
        )
        if needs_update:
            rescored.append(rescore_row(row))
            n_updated += 1
        else:
            rescored.append(row)

    # Rewrite CSV
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rescored)

    print(f"✅ Rescored {n_updated} rows out of {len(rows)} total")
    print(f"   CSV rewritten: {CSV_PATH}")
