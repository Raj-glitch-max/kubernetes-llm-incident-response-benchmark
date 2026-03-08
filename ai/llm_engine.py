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

def analyze_incident(incident: IncidentInput, model_choice: str = "gpt-4-turbo") -> tuple[LLMOutput, float]:
    """
    Analyzes an incident using the specified LLM.
    Returns the parsed LLMOutput and the latency in seconds.
    """
    start_time = time.time()
    
    if model_choice == "gpt-4-turbo":
        result = call_gpt4_turbo(incident)
    elif model_choice == "claude-3-sonnet":
        result = call_claude3_sonnet(incident)
    else:
        raise ValueError(f"Unknown model: {model_choice}")
        
    end_time = time.time()
    latency = end_time - start_time
    
    return result, latency
