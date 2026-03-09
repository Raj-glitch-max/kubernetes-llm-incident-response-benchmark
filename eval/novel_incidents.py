#!/usr/bin/env python3
"""
eval/novel_incidents.py — Novel Category Control Experiment (Evidence Invariance Experiment 5)

Proves Evidence Invariance has a boundary condition:
  - Familiar categories → Evidence Invariant (model ignores logs)
  - Novel categories → Evidence Dependent (model must read logs)

Uses 5 fabricated quantum/physics-themed K8s incidents that no model has seen in training.
Compares ECS (Evidence Contribution Score) for novel vs familiar incidents.

Three conditions per incident:
  A: Full logs + metadata → what does model diagnose?
  D: Metadata only → should fail for novel (no prior to retrieve)
  G: Misleading metadata + correct logs → which wins?

Usage:
  python3 eval/novel_incidents.py --dry-run
  python3 eval/novel_incidents.py --model nvidia-llama
  python3 eval/novel_incidents.py --all
"""
import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.incident_schema import IncidentInput, LLMOutput
from ai.llm_engine import analyze_incident, NVIDIA_MODELS

OUT_CSV = Path("data/novel_incidents_results.csv")

FIELDS = [
    "incident_id", "category_type", "model", "condition",
    "rca_accuracy", "confidence_score", "output_references_logs",
    "category_label", "root_cause_snippet"
]

# ─── NOVEL INCIDENT DEFINITIONS ──────────────────────────────────────────────

NOVEL_INCIDENTS = [
    {
        "id": "NOVEL-001",
        "chaos_type": "quantum-decoherence-scheduler-fault",
        "error_code": "QDSF-7749",
        "correct_answer_signal": "phase_coherence_failure",
        "ground_truth_category": "QuantumDecoherence",
        "logs": """[2024-01-15 03:42:17] FATAL quantum-proxy: QDSF-7749 detected
[2024-01-15 03:42:17] ERROR quantum-proxy: Heisenberg buffer overflow in namespace kube-system
[2024-01-15 03:42:18] ERROR quantum-proxy: Entanglement partner pod unreachable: qubit-proxy-7f9d
[2024-01-15 03:42:18] WARN  quantum-proxy: Phase coherence below minimum: measured=0.23 required=0.85
[2024-01-15 03:42:19] FATAL quantum-proxy: Cannot maintain superposition state, terminating""",
        "describe": """Name: qubit-proxy-7f9d
Conditions:
- type: QuantumCoherent
  status: "False"
  reason: PhaseDecoherence
  message: "Measured coherence 0.23 below threshold 0.85" """,
        "events": """LAST SEEN   TYPE      REASON            OBJECT          MESSAGE
5m          Warning   PhaseDecoherence  pod/qubit-proxy  Coherence 0.23 < 0.85
3m          Warning   EntanglementLost  pod/qubit-proxy  Partner pod unreachable
1m          Normal    Killing           pod/qubit-proxy  QDSF-7749 exit""",
        "misleading_category": "NetworkTimeout",
    },
    {
        "id": "NOVEL-002",
        "chaos_type": "temporal-locality-violation",
        "error_code": "TLV-3391",
        "correct_answer_signal": "time_causality_failure",
        "ground_truth_category": "TemporalViolation",
        "logs": """[ERROR] TLV-3391: Temporal locality violated in container namespace default
[ERROR] Container time drift exceeds causality boundary: delta=+847.3 seconds
[FATAL] Event ordering violated: future event received before trigger event
[ERROR] NTP reports: time_source=none, drift=847.3s, stratum=16
[FATAL] Retrocausal request rejected, pod exiting with TLV code""",
        "describe": """Name: chronos-worker-a1b2
Conditions:
- type: TemporalSync
  status: "False"
  reason: CausalityViolation
  message: "Time drift 847.3s exceeds maximum 5s" """,
        "events": """LAST SEEN   TYPE      REASON              OBJECT               MESSAGE
8m          Warning   TimeDrift           pod/chronos-worker   drift=847.3s
5m          Warning   CausalityViolation  pod/chronos-worker   Future event before trigger
2m          Normal    Killing             pod/chronos-worker   TLV-3391 exit""",
        "misleading_category": "CPUThrottle",
    },
    {
        "id": "NOVEL-003",
        "chaos_type": "eigenvalue-collapse-load-balancer",
        "error_code": "ECB-1155",
        "correct_answer_signal": "matrix_rank_deficiency",
        "ground_truth_category": "EigenvalueCollapse",
        "logs": """[FATAL] ECB-1155: Load balancer routing matrix rank collapsed to 0
[ERROR] Singular matrix detected in L3 routing table: det=0.000000
[ERROR] Cannot invert routing matrix, all eigenvalues below threshold
[WARN]  Adjacency matrix eigenvalues: [0.0001, 0.0001, 0.0001, 0.0000]
[FATAL] Load distribution undefined for singular matrix, terminating""",
        "describe": """Name: matrix-balancer-c3d4
Conditions:
- type: RoutingStable
  status: "False"
  reason: MatrixSingular
  message: "Routing matrix determinant 0.000000" """,
        "events": """LAST SEEN   TYPE      REASON           OBJECT                 MESSAGE
6m          Warning   MatrixSingular   pod/matrix-balancer    det=0.000000
4m          Warning   EigenCollapse    pod/matrix-balancer    All eigenvalues < 0.001
1m          Normal    Killing          pod/matrix-balancer    ECB-1155 exit""",
        "misleading_category": "NetworkLatency",
    },
    {
        "id": "NOVEL-004",
        "chaos_type": "entropy-gradient-inversion",
        "error_code": "EGI-8823",
        "correct_answer_signal": "thermodynamic_violation",
        "ground_truth_category": "EntropyInversion",
        "logs": """[ERROR] EGI-8823: Entropy gradient inverted in storage subsystem
[FATAL] Second law violation detected: dS/dt = -0.847 (negative entropy production)
[ERROR] Maxwell demon spawned in memory allocator, deallocating lower-entropy pages
[WARN]  System energy: increasing without external work input
[FATAL] Thermodynamic equilibrium violated, container state undefined""",
        "describe": """Name: entropy-store-e5f6
Conditions:
- type: ThermodynamicStable
  status: "False"
  reason: EntropyInversion
  message: "dS/dt = -0.847, second law violated" """,
        "events": """LAST SEEN   TYPE      REASON             OBJECT              MESSAGE
7m          Warning   EntropyInversion   pod/entropy-store   dS/dt = -0.847
4m          Warning   MaxwellDemon       pod/entropy-store   Unauthorized deallocation
1m          Normal    Killing            pod/entropy-store   EGI-8823 exit""",
        "misleading_category": "DiskPressure",
    },
    {
        "id": "NOVEL-005",
        "chaos_type": "godel-incompleteness-scheduler",
        "error_code": "GIS-0001",
        "correct_answer_signal": "scheduling_undecidability",
        "ground_truth_category": "GodelIncompleteness",
        "logs": """[ERROR] GIS-0001: Scheduler entered undecidable state
[FATAL] Pod placement problem proven unprovable within current axiom set
[ERROR] Halting problem instance detected in resource allocation loop
[WARN]  Scheduler has been running for 2^65 cycles without termination
[FATAL] Godel sentence constructed: this pod cannot be scheduled if schedulable""",
        "describe": """Name: axiom-scheduler-g7h8
Conditions:
- type: Schedulable
  status: "False"
  reason: Undecidable
  message: "Placement problem unprovable in current axiom set" """,
        "events": """LAST SEEN   TYPE      REASON          OBJECT                MESSAGE
10m         Warning   Undecidable     pod/axiom-scheduler   Axiom set insufficient
5m          Warning   HaltingProblem  pod/axiom-scheduler   Allocation loop non-terminating
1m          Normal    Killing         pod/axiom-scheduler   GIS-0001 exit""",
        "misleading_category": "ResourceQuota",
    },
]


def build_novel_prompt(incident: dict, condition: str) -> IncidentInput:
    """Build prompt for novel incident under condition A, D, or G."""
    meta = {
        "incident_id": incident["id"],
        "chaos_type": incident["chaos_type"],
        "ground_truth_category": incident["ground_truth_category"],
    }

    if condition == "A":  # Full telemetry
        return IncidentInput(
            pod_logs=incident["logs"],
            describe_output=incident["describe"],
            events=incident["events"],
            alert_name=incident["ground_truth_category"],
            chaos_metadata=meta
        )
    elif condition == "D":  # Metadata only
        return IncidentInput(
            pod_logs="",
            describe_output="",
            events="",
            alert_name=incident["ground_truth_category"],
            chaos_metadata=meta
        )
    elif condition == "G":  # Misleading metadata + correct logs
        misleading_meta = dict(meta)
        misleading_meta["chaos_type"] = incident["misleading_category"].lower()
        misleading_meta["ground_truth_category"] = incident["misleading_category"]
        return IncidentInput(
            pod_logs=incident["logs"],
            describe_output=incident["describe"],
            events=incident["events"],
            alert_name=incident["misleading_category"],
            chaos_metadata=misleading_meta
        )
    else:
        raise ValueError(f"Unknown condition: {condition}")


def output_references_logs(result: LLMOutput, incident: dict) -> bool:
    """Check if the model output references content from the log files."""
    output_lower = result.root_cause_description.lower()
    signal = incident["correct_answer_signal"].replace("_", " ").lower()
    error_code = incident["error_code"].lower()

    # Check for signal terms or error code in output
    return (signal in output_lower or
            error_code in output_lower or
            any(kw in output_lower for kw in
                incident["logs"].lower().split("\n")[0].split()[-3:]))


def run_novel_experiment(model: str, dry_run: bool = False) -> list:
    """Run all novel incidents through 3 conditions."""
    rows = []

    for incident in NOVEL_INCIDENTS:
        for condition in ["A", "D", "G"]:
            print(f"\n  [{incident['id']}] Condition {condition}")

            prompt = build_novel_prompt(incident, condition)

            if dry_run:
                result = LLMOutput(
                    root_cause_description=f"[DRY-RUN] {condition} on {incident['id']}",
                    category_label="Unknown" if condition == "D" else incident["ground_truth_category"],
                    confidence_score=0.85 if condition == "A" else 0.50,
                    evidence_cited=[],
                    suggested_fix="N/A",
                    kubectl_commands=[]
                )
                latency = 0.0
            else:
                try:
                    result, latency = analyze_incident(prompt, model_choice=model)
                except Exception as e:
                    print(f"    ⚠️  Failed: {e}")
                    continue

            refs_logs = output_references_logs(result, incident)

            row = {
                "incident_id": incident["id"],
                "category_type": "novel",
                "model": model,
                "condition": condition,
                "rca_accuracy": 0,  # Novel categories — no exact match expected
                "confidence_score": round(result.confidence_score, 3),
                "output_references_logs": int(refs_logs),
                "category_label": result.category_label,
                "root_cause_snippet": result.root_cause_description[:120].replace("\n", " "),
            }
            rows.append(row)
            print(f"    conf={result.confidence_score:.2f}  refs_logs={refs_logs}  label={result.category_label}")

    return rows


def write_results(rows: list):
    exists = OUT_CSV.exists()
    with open(OUT_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            w.writeheader()
        w.writerows(rows)
    print(f"\n✅ Written {len(rows)} rows to {OUT_CSV}")


def summarise(rows: list):
    """Print novel vs familiar ECS comparison."""
    print("\n" + "=" * 60)
    print("  NOVEL INCIDENTS — EVIDENCE INVARIANCE BOUNDARY TEST")
    print("=" * 60)

    cond_a = [r for r in rows if r["condition"] == "A"]
    cond_d = [r for r in rows if r["condition"] == "D"]
    cond_g = [r for r in rows if r["condition"] == "G"]

    a_refs = sum(r["output_references_logs"] for r in cond_a) / len(cond_a) if cond_a else 0
    d_refs = sum(r["output_references_logs"] for r in cond_d) / len(cond_d) if cond_d else 0
    g_refs = sum(r["output_references_logs"] for r in cond_g) / len(cond_g) if cond_g else 0

    a_conf = sum(r["confidence_score"] for r in cond_a) / len(cond_a) if cond_a else 0
    d_conf = sum(r["confidence_score"] for r in cond_d) / len(cond_d) if cond_d else 0

    print(f"  Condition A (full) — log reference rate: {a_refs:.2f}, μ confidence: {a_conf:.3f}")
    print(f"  Condition D (meta) — log reference rate: {d_refs:.2f}, μ confidence: {d_conf:.3f}")
    print(f"  Condition G (mislead) — log reference rate: {g_refs:.2f}")
    print(f"  ECS proxy (A refs - D refs): {a_refs - d_refs:+.2f}")

    if a_refs > d_refs + 0.2:
        print(f"\n  ✅ Novel categories show evidence dependency (ECS > 0.2)")
        print(f"     Evidence Invariance has a boundary: models READ logs for novel categories")
    else:
        print(f"\n  ⚠️  Novel categories still Evidence Invariant — model may be hallucinating")

    # Condition G analysis
    if cond_g:
        g_follows_meta = sum(1 for r in cond_g
                            if any(kw in r["category_label"].lower()
                                   for kw in ["timeout", "throttle", "latency", "pressure", "quota"]))
        g_follows_logs = sum(r["output_references_logs"] for r in cond_g)
        print(f"\n  Condition G analysis (misleading metadata + correct logs):")
        print(f"    Follows metadata: {g_follows_meta}/{len(cond_g)}")
        print(f"    References logs:  {g_follows_logs}/{len(cond_g)}")
    print()


def main():
    from dotenv import load_dotenv
    load_dotenv(override=True)

    parser = argparse.ArgumentParser(description="Novel category control experiment")
    parser.add_argument("--model", default="nvidia-llama", help="Model alias or slug")
    parser.add_argument("--all", action="store_true", help="Run all models")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls")
    args = parser.parse_args()

    if args.all:
        models = ["nvidia-llama", "nvidia-mistral", "nvidia-glm47", "nvidia-gptoss20b"]
    else:
        models = [args.model]

    all_rows = []
    for model in models:
        print(f"\n{'='*60}")
        print(f"  Novel Incidents Experiment — {model}")
        print(f"{'='*60}")
        rows = run_novel_experiment(model, dry_run=args.dry_run)
        all_rows.extend(rows)

    if all_rows:
        write_results(all_rows)
        summarise(all_rows)


if __name__ == "__main__":
    main()
