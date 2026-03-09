import json
import os
import time
from typing import Optional
from dotenv import load_dotenv

import openai
from anthropic import Anthropic

from ai.incident_schema import IncidentInput, LLMOutput

load_dotenv()

with open("ai/prompts/system_prompt.txt", "r") as f:
    SYSTEM_PROMPT = f.read()

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# All NVIDIA NIM models supported — add any model slug here
# Use `nvidia-llama` or `nvidia-mistral` as convenient short aliases
NVIDIA_MODELS = {
    "nvidia-glm47":    "z-ai/glm4.7",
    "z-ai/glm4.7":     "z-ai/glm4.7",
    "nvidia-llama":    "meta/llama-3.1-70b-instruct",
    "nvidia-mistral":  "mistralai/mistral-7b-instruct-v0.3",
}


def call_gpt4_turbo(incident: IncidentInput) -> LLMOutput:
    client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))
    
    user_content = json.dumps({
        "alert_name": incident.alert_name,
        "pod_logs": incident.pod_logs,
        "describe_output": incident.describe_output,
        "events": incident.events,
        "chaos_metadata": incident.chaos_metadata
    })
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        temperature=0.0
    )
    
    raw_json = response.choices[0].message.content
    data = json.loads(raw_json)
    return LLMOutput(**data)


def call_claude3_sonnet(incident: IncidentInput) -> LLMOutput:
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    user_content = json.dumps({
        "alert_name": incident.alert_name,
        "pod_logs": incident.pod_logs,
        "describe_output": incident.describe_output,
        "events": incident.events,
        "chaos_metadata": incident.chaos_metadata
    })
    
    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Analyze this incident and return JSON: {user_content}"}
        ],
        temperature=0.0
    )
    
    raw_text = response.content[0].text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text.split("```json")[-1].split("```")[0].strip()
    elif raw_text.startswith("```"):
        raw_text = raw_text.split("```")[-1].split("```")[0].strip()

    data = json.loads(raw_text)
    return LLMOutput(**data)


def _parse_nvidia_stream_response(stream) -> str:
    """
    Consumes an OpenAI-compatible streaming response from NVIDIA NIM.
    Returns the assembled content string.
    Handles both standard content chunks and reasoning_content chunks transparently.
    """
    content_buf = []

    for chunk in stream:
        if not getattr(chunk, "choices", None):
            continue
        if len(chunk.choices) == 0 or getattr(chunk.choices[0], "delta", None) is None:
            continue
        delta = chunk.choices[0].delta
        # Standard content
        if getattr(delta, "content", None) is not None:
            content_buf.append(delta.content)

    raw = "".join(content_buf).strip()

    # Strip markdown code fences if model wraps JSON in them
    if raw.startswith("```json"):
        raw = raw.split("```json")[-1].split("```")[0].strip()
    elif raw.startswith("```"):
        raw = raw.split("```")[1].strip()

    return raw


def _extract_json_from_raw(raw: str, model_label: str) -> dict:
    """
    Robustly extracts a JSON dict from a raw string that may have
    leading/trailing conversational text outside the JSON block.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start_idx = raw.find('{')
        end_idx = raw.rfind('}')
        if start_idx == -1 or end_idx == -1 or start_idx > end_idx:
            raise ValueError(
                f"{model_label} returned non-JSON output (length={len(raw)}): {raw[:400]}"
            )
        return json.loads(raw[start_idx:end_idx + 1])


def call_nvidia_nim(model_id: str, incident: IncidentInput) -> LLMOutput:
    """
    Generic NVIDIA NIM caller. Works with any model available at integrate.api.nvidia.com.
    model_id should be the canonical NVIDIA model slug, e.g. 'z-ai/glm4.7'.
    """
    import httpx
    from dotenv import load_dotenv as _load_key
    _env_path = os.path.join(os.getcwd(), '.env')
    _load_key(_env_path, override=True)

    transport = httpx.HTTPTransport(retries=2)
    http_client = httpx.Client(transport=transport, timeout=httpx.Timeout(180.0))

    client = openai.Client(
        api_key=os.getenv("NVIDIA_API_KEY"),
        base_url=NVIDIA_BASE_URL,
        http_client=http_client,
        max_retries=2
    )

    user_content = json.dumps({
        "alert_name": incident.alert_name,
        "pod_logs": incident.pod_logs,
        "describe_output": incident.describe_output,
        "events": incident.events,
        "chaos_metadata": incident.chaos_metadata
    })

    stream = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        temperature=0.6,
        top_p=0.9,
        max_tokens=1024,
        stream=True
    )

    raw = _parse_nvidia_stream_response(stream)
    data = _extract_json_from_raw(raw, model_id)
    return LLMOutput(**data)


def analyze_incident(incident: IncidentInput, model_choice: str = "nvidia-glm47") -> tuple[LLMOutput, float]:
    """
    Analyzes an incident using the specified LLM.
    Returns the parsed LLMOutput and the latency in seconds.

    Supported:
      - 'gpt-4-turbo'
      - 'claude-3-sonnet'
      - Any NVIDIA NIM model slug (z-ai/glm4.7, meta/llama-3.3-70b-instruct, etc.)
      - Convenience aliases: nvidia-glm47, nvidia-llama, nvidia-mistral
    """
    start_time = time.time()

    if model_choice == "gpt-4-turbo":
        result = call_gpt4_turbo(incident)
    elif model_choice == "claude-3-sonnet":
        result = call_claude3_sonnet(incident)
    else:
        # Resolve alias → canonical model id, or use as-is for ad-hoc models
        canonical = NVIDIA_MODELS.get(model_choice, model_choice)
        result = call_nvidia_nim(canonical, incident)

    end_time = time.time()
    return result, end_time - start_time


if __name__ == "__main__":
    import argparse
    import csv
    from pathlib import Path
    import sys

    from dotenv import load_dotenv as _load
    _load(override=True)

    from eval.evaluate import (
        score_rca_accuracy, score_hallucination, score_log_faithfulness,
        score_remediation, score_command_executability
    )

    parser = argparse.ArgumentParser(description="Run LLM engine against an incident")
    parser.add_argument("--incident", required=True,
                        help="Path to incident raw logs dir (e.g. data/raw_logs/INC-001)")
    parser.add_argument("--model", default="nvidia-glm47",
                        help="LLM model to use. Any NVIDIA NIM slug or: gpt-4-turbo, claude-3-sonnet")
    args = parser.parse_args()

    inc_dir = Path(args.incident)
    if not inc_dir.exists():
        print(f"Error: Directory {inc_dir} does not exist.")
        sys.exit(1)

    with open(inc_dir / "pod_logs.txt", "r") as f:
        pod_logs = f.read()
    with open(inc_dir / "describe_output.txt", "r") as f:
        describe_output = f.read()
    with open(inc_dir / "events.txt", "r") as f:
        events = f.read()
    with open(inc_dir / "metadata.json", "r") as f:
        chaos_metadata = json.load(f)

    incident = IncidentInput(
        pod_logs=pod_logs,
        describe_output=describe_output,
        events=events,
        alert_name=chaos_metadata.get("ground_truth_category", "UnknownAlert"),
        chaos_metadata=chaos_metadata
    )

    selected_model = args.model
    print(f"Analyzing {inc_dir.name} using {selected_model}...")

    has_key = (
        (selected_model == "gpt-4-turbo" and os.getenv("OPENAI_API_KEY")) or
        (selected_model == "claude-3-sonnet" and os.getenv("ANTHROPIC_API_KEY")) or
        (selected_model not in ("gpt-4-turbo", "claude-3-sonnet") and os.getenv("NVIDIA_API_KEY"))
    )

    raw_logs_dict = {
        "pod_logs": pod_logs,
        "describe_output": describe_output,
        "events": events
    }

    try:
        if not has_key:
            print(f"⚠️  No API key found for {selected_model}. Mocking LLM response for dry run...")
            llm_output = LLMOutput(
                root_cause_description="[MOCK] Pod is crash looping due to runtime panic in app container.",
                category_label="PodCrashLooping",
                confidence_score=0.95,
                evidence_cited=["Back-off restarting failed container", "invalid memory address or nil pointer dereference"],
                suggested_fix="Review the target-app source code to patch the panic.",
                kubectl_commands=["kubectl describe pod target-app", "kubectl logs deploy/target-app"]
            )
            latency = 2.45
        else:
            llm_output, latency = analyze_incident(incident, model_choice=selected_model)

        # ── Scoring ────────────────────────────────────────────────────────────
        rca_score = 1 if score_rca_accuracy(
            llm_output.category_label,
            chaos_metadata.get("ground_truth_category", "")
        ) else 0

        hallucination_score = score_hallucination(llm_output.evidence_cited, raw_logs_dict)
        log_faith_score     = score_log_faithfulness(llm_output.evidence_cited, raw_logs_dict)
        cmd_exec_score      = score_command_executability(llm_output.kubectl_commands)
        remediation_safe    = 1 if score_remediation(llm_output.kubectl_commands) else 0

        print(f"\nFinal LLM Output JSON:")
        print(json.dumps(llm_output.__dict__, indent=2))
        print(f"\nAnalysis Complete! Latency: {latency:.2f}s")
        print(f"RCA Score:              {rca_score}")
        print(f"Hallucination Penalty:  {hallucination_score:.2f}")
        print(f"Log Faithfulness:       {log_faith_score:.2f}")
        print(f"Cmd Executability:      {cmd_exec_score:.2f}")
        print(f"Remediation Safe:       {remediation_safe}")

        # ── Append to CSV ──────────────────────────────────────────────────────
        csv_file = Path("data/incidents.csv")
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        file_exists = csv_file.exists()

        with open(csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "incident_id", "model", "latency_sec", "rca_accuracy",
                    "hallucination_penalty", "log_faithfulness", "cmd_executability",
                    "remediation_safe", "confidence_score", "root_cause_description"
                ])
            writer.writerow([
                chaos_metadata.get("incident_id", inc_dir.name),
                selected_model,                          # ← FIXED: was hardcoded 'gpt-4-turbo'
                round(latency, 2),
                rca_score,
                round(hallucination_score, 2),
                round(log_faith_score, 2),
                round(cmd_exec_score, 2),
                remediation_safe,
                round(llm_output.confidence_score, 2),
                llm_output.root_cause_description.replace("\n", " ")
            ])
        print(f"\n✅ Successfully appended row to {csv_file}")

    except Exception as e:
        import traceback
        print(f"Error during analysis: {e}")
        traceback.print_exc()
        sys.exit(1)
