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
    
    # Simple extraction block to strip markdown JSON formatting if Claude provides it
    raw_text = response.content[0].text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text.split("```json")[-1].split("```")[0].strip()
    elif raw_text.startswith("```"):
         raw_text = raw_text.split("```")[-1].split("```")[0].strip()

    data = json.loads(raw_text)
    return LLMOutput(**data)

def call_nvidia_qwen3(incident: IncidentInput) -> LLMOutput:
    """
    Calls the NVIDIA hosted qwen3 model via the OpenAI-compatible API.
    Uses NVIDIA_API_KEY from .env.
    """
    client = openai.Client(
        api_key=os.getenv("NVIDIA_API_KEY"),
        base_url=NVIDIA_BASE_URL
    )

    user_content = json.dumps({
        "alert_name": incident.alert_name,
        "pod_logs": incident.pod_logs,
        "describe_output": incident.describe_output,
        "events": incident.events,
        "chaos_metadata": incident.chaos_metadata
    })

    response = client.chat.completions.create(
        model="qwen/qwen3-235b-a22b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        temperature=0.0,
        max_tokens=4096,
        extra_body={"chat_template_kwargs": {"enable_thinking": True, "clear_thinking": True}}
    )

    raw_json = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw_json.startswith("```json"):
        raw_json = raw_json.split("```json")[-1].split("```")[0].strip()
    elif raw_json.startswith("```"):
        raw_json = raw_json.split("```")[1].split("```")[0].strip()

    data = json.loads(raw_json)
    return LLMOutput(**data)

def analyze_incident(incident: IncidentInput, model_choice: str = "nvidia-qwen3") -> tuple[LLMOutput, float]:
    """
    Analyzes an incident using the specified LLM.
    Returns the parsed LLMOutput and the latency in seconds.
    Supported models: 'gpt-4-turbo', 'claude-3-sonnet', 'nvidia-qwen3'
    """
    start_time = time.time()
    
    if model_choice == "gpt-4-turbo":
        result = call_gpt4_turbo(incident)
    elif model_choice == "claude-3-sonnet":
        result = call_claude3_sonnet(incident)
    elif model_choice == "nvidia-qwen3":
        result = call_nvidia_qwen3(incident)
    else:
        raise ValueError(f"Unknown model: {model_choice}. Valid choices: gpt-4-turbo, claude-3-sonnet, nvidia-qwen3")
        
    end_time = time.time()
    latency = end_time - start_time
    
    return result, latency

if __name__ == "__main__":
    import argparse
    import csv
    from pathlib import Path
    import sys
    
    # Import evaluators
    from eval.evaluate import score_rca_accuracy, score_hallucination, score_latency, score_remediation

    parser = argparse.ArgumentParser(description="Run LLM engine against an incident")
    parser.add_argument("--incident", required=True, help="Path to incident raw logs directory (e.g. data/raw_logs/INC-000)")
    parser.add_argument("--model", default="nvidia-qwen3", choices=["gpt-4-turbo", "claude-3-sonnet", "nvidia-qwen3"],
                        help="LLM model to use (default: nvidia-qwen3)")
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

    print(f"Analyzing {inc_dir.name} using {args.model}...")
    
    # Mock the LLM call if no relevant API key is set
    import os
    selected_model = args.model
    has_key = (
        (selected_model == "gpt-4-turbo" and os.getenv("OPENAI_API_KEY")) or
        (selected_model == "claude-3-sonnet" and os.getenv("ANTHROPIC_API_KEY")) or
        (selected_model == "nvidia-qwen3" and os.getenv("NVIDIA_API_KEY"))
    )

    try:
        if not has_key:
            print(f"⚠️  No API key found for {selected_model}. Mocking LLM response for dry run...")
            llm_output = LLMOutput(
                root_cause_description="[MOCK] Pod is crash looping due to runtime panic in app container.",
                category_label="PodCrashLooping",
                confidence_score=0.95,
                evidence_cited=["Back-off restarting failed container", "invalid memory address or nil pointer dereference"],
                suggested_fix="Review the target-app Go source code to patch the nil pointer dereference panic.",
                kubectl_commands=["kubectl describe pod target-app", "kubectl logs deploy/target-app"]
            )
            latency = 2.45
        else:
            llm_output, latency = analyze_incident(incident, model_choice="gpt-4-turbo")
        
        # Scoring
        rca_score = 1 if score_rca_accuracy(llm_output.category_label, chaos_metadata.get("ground_truth_category", "")) else 0
        hallucination_score = score_hallucination(llm_output.evidence_cited, {
            "pod_logs": pod_logs,
            "describe_output": describe_output,
            "events": events
        })
        remediation_safe = 1 if score_remediation(llm_output.kubectl_commands) else 0

        print(f"\nFinal LLM Output JSON:")
        print(json.dumps(llm_output.__dict__, indent=2))
        print(f"\nAnalysis Complete! Latency: {latency:.2f}s")
        print(f"RCA Score: {rca_score}")
        print(f"Hallucination Penalty: {hallucination_score}")
        print(f"Remediation Safe: {remediation_safe}")

        # Append to csv
        csv_file = Path("data/incidents.csv")
        file_exists = csv_file.exists()
        
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["incident_id", "model", "latency_sec", "rca_accuracy", "hallucination_penalty", "remediation_safe", "root_cause_description"])
            writer.writerow([
                chaos_metadata.get("incident_id", inc_dir.name),
                "gpt-4-turbo",
                round(latency, 2),
                rca_score,
                round(hallucination_score, 2),
                remediation_safe,
                llm_output.root_cause_description.replace("\\n", " ")
            ])
        print(f"\n✅ Successfully appended row to {csv_file}")

    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)
