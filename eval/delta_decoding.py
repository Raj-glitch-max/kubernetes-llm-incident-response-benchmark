#!/usr/bin/env python3
"""
eval/delta_decoding.py — The Causal Fix (Experiment 3)

Implements: output = argmax((residual_full - residual_meta) @ W_U)

This script provides a 'DeltaLLM' wrapper that subtracts the 'metadata-only' 
residual stream from the 'full-telemetry' residual stream at the final layer, 
isolating the specific informational contribution of the evidence.

Usage:
  python3 eval/delta_decoding.py --model distilgpt2 --incident data/domain_replication/med.json
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import argparse
import json
from pathlib import Path

class DeltaLLM:
    def __init__(self, model_name="distilgpt2"):
        print(f"Loading {model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(model_name, output_hidden_states=True)
        self.model.eval()

    def get_last_hidden_state(self, prompt):
        inputs = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
        # Final layer hidden state for the last token
        last_hidden = outputs.hidden_states[-1][:, -1, :]
        return last_hidden

    def delta_decode(self, prompt_full, prompt_meta):
        h_full = self.get_last_hidden_state(prompt_full)
        h_meta = self.get_last_hidden_state(prompt_meta)

        # Δh = h_full - h_meta
        delta_h = h_full - h_meta

        # Map back to logits using the LM Head (W_U)
        with torch.no_grad():
            logits = self.model.lm_head(delta_h)
        
        # Get top tokens
        probs = torch.softmax(logits, dim=-1)
        top_k = torch.topk(probs, 5)
        
        results = []
        for i in range(5):
            token_id = top_k.indices[0, i].item()
            token_text = self.tokenizer.decode([token_id])
            score = top_k.values[0, i].item()
            results.append((token_text, score))
        
        return results

def format_incident_prompts(incident_path):
    path = Path(incident_path)
    if path.is_dir():
        # Handle benchmark directory structure
        with open(path / "metadata.json", 'r') as f:
            meta_data = json.load(f)
        with open(path / "pod_logs.txt", 'r') as f:
            logs = f.read()
        with open(path / "events.txt", 'r') as f:
            events = f.read()
        
        meta_str = json.dumps(meta_data.get("chaos_metadata", {}))
        prompt_meta = f"Incident Metadata: {meta_str}\n\nRoot Cause Analysis:"
        telemetry = f"Logs: {logs}\nEvents: {events}"
        prompt_full = f"Incident Metadata: {meta_str}\n{telemetry}\n\nRoot Cause Analysis:"
        return prompt_full, prompt_meta
    else:
        # Handle flat JSON file (Domain Replication)
        with open(path, 'r') as f:
            data = json.load(f)
        meta_str = json.dumps(data.get("chaos_metadata", {}))
        prompt_meta = f"Incident Metadata: {meta_str}\n\nRoot Cause Analysis:"
        telemetry = f"Logs: {data.get('pod_logs','')}\nEvents: {data.get('events','')}"
        prompt_full = f"Incident Metadata: {meta_str}\n{telemetry}\n\nRoot Cause Analysis:"
        return prompt_full, prompt_meta

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="distilgpt2")
    parser.add_argument("--incident", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        import torch
        import transformers
    except ImportError:
        print("❌ torch/transformers not installed. Run 'pip install torch transformers'.")
        return

    full, meta = format_incident_prompts(args.incident)
    
    print("\n" + "="*60)
    print(f" Δ-DECODING: {Path(args.incident).name}")
    print("="*60)
    
    llm = DeltaLLM(args.model)
    
    print("\n--- Standard Decoding (Full Prompt) ---")
    h_full = llm.get_last_hidden_state(full)
    logits_std = llm.model.lm_head(h_full)
    std_top = torch.topk(torch.softmax(logits_std, dim=-1), 3)
    for i in range(3):
        print(f"  {llm.tokenizer.decode([std_top.indices[0,i].item()]):15s} | {std_top.values[0,i].item():.4f}")

    print("\n--- Metadata-Only Decoding (Condition D) ---")
    h_meta = llm.get_last_hidden_state(meta)
    logits_meta = llm.model.lm_head(h_meta)
    meta_top = torch.topk(torch.softmax(logits_meta, dim=-1), 3)
    for i in range(3):
        print(f"  {llm.tokenizer.decode([meta_top.indices[0,i].item()]):15s} | {meta_top.values[0,i].item():.4f}")

    print("\n--- Δ-DECODING (Full - Meta) ---")
    results = llm.delta_decode(full, meta)
    for token, score in results[:3]:
        print(f"  {token:15s} | {score:.4f}  [EVIDENCE SIGNAL]")

    print("\nConclusion:")
    std_top_token = llm.tokenizer.decode([std_top.indices[0,0].item()])
    delta_top_token = results[0][0]
    if std_top_token != delta_top_token:
        print(f"✅ SUCCESS: Δ-Decoding shifted prediction from '{std_top_token}' to '{delta_top_token}'")
    else:
        print(f"⚠️  STASIS: Prediction remained '{std_top_token}'. Metadata prior still dominates.")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
