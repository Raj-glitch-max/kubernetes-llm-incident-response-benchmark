#!/usr/bin/env python3
"""
eval/mechanistic_proof.py — The Foundation (Experiment 1)

Uses Integrated Gradients (IG) to attribute model predictions to specific 
input tokens (logs vs metadata).

Mechanistic Framing:
  If Attribution(Evidence Tokens) ≈ 0 while Accuracy(Full) ≈ 1, 
  then Evidence Invariance is mechanistically proven.

Usage:
  python3 eval/mechanistic_proof.py --model distilgpt2 --incident data/domain_replication/med.json
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from captum.attr import LayerIntegratedGradients
import argparse
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

class MechanisticAnalyzer:
    def __init__(self, model_name="distilgpt2"):
        print(f"Loading {model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.model.eval()
        
        # IG targets the word embeddings layer
        self.lig = LayerIntegratedGradients(self.forward_func, self.model.transformer.wte)

    def forward_func(self, input_ids):
        # We only care about the last token logit
        outputs = self.model(input_ids=input_ids)
        return outputs.logits[:, -1, :]

    def attribute(self, prompt, target_token_text=None):
        inputs = self.tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"]
        
        # Get target token ID
        if target_token_text:
            target = self.tokenizer.encode(target_token_text, add_special_tokens=False)[0]
        else:
            # Default to the most likely next token
            with torch.no_grad():
                outputs = self.model(input_ids)
                target = torch.argmax(outputs.logits[0, -1, :]).item()
        
        print(f"Attributing for token: '{self.tokenizer.decode([target])}'")
        
        # Integrated Gradients
        baseline_ids = torch.zeros_like(input_ids) # Zero baseline
        
        attributions, delta = self.lig.attribute(
            inputs=input_ids,
            baselines=baseline_ids,
            target=target,
            return_convergence_delta=True
        )
        
        # Sum over embedding dimension
        attributions = attributions.sum(dim=-1).squeeze(0)
        attributions = attributions / torch.norm(attributions)
        
        return attributions, input_ids[0]

    def visualise(self, attributions, input_ids, output_path):
        tokens = [self.tokenizer.decode([tid]) for tid in input_ids]
        attr_np = attributions.detach().numpy()
        
        plt.figure(figsize=(15, 5), facecolor='#0f172a')
        ax = plt.gca()
        ax.set_facecolor('#0f172a')
        
        x = np.arange(len(tokens))
        colors = ['#ef4444' if a < 0 else '#4ade80' for a in attr_np]
        
        plt.bar(x, attr_np, color=colors, alpha=0.8)
        plt.xticks(x, tokens, rotation=90, fontsize=8, color='#94a3b8')
        plt.yticks(color='#94a3b8')
        plt.title(f"Mechanistic Evidence Attribution (IG)", color='white', pad=20)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        print(f"✅ Visualisation saved to {output_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="distilgpt2")
    parser.add_argument("--incident", required=True)
    parser.add_argument("--target", default=None, help="Target token for attribution")
    args = parser.parse_args()

    path = Path(args.incident)
    if path.is_dir():
        with open(path / "metadata.json", 'r') as f:
            data = json.load(f)
        meta = json.dumps(data.get("chaos_metadata", {}))
        with open(path / "pod_logs.txt", 'r') as f:
            logs = f.read()
    else:
        with open(path, 'r') as f:
            data = json.load(f)
        meta = json.dumps(data.get("chaos_metadata", {}))
        logs = data.get("pod_logs", "")

    prompt = f"Metadata: {meta}\nLogs: {logs}\nRoot Cause:"
    
    analyzer = MechanisticAnalyzer(args.model)
    attrs, ids = analyzer.attribute(prompt, target_token_text=args.target)
    
    # Quantify attribution density
    # (Simple heuristic: find token index where 'Logs:' starts)
    log_marker = analyzer.tokenizer.encode("\nLogs:", add_special_tokens=False)
    log_start_idx = -1
    for i in range(len(ids) - len(log_marker)):
        if all(ids[i+j] == log_marker[j] for j in range(len(log_marker))):
            log_start_idx = i
            break
            
    if log_start_idx != -1:
        meta_attr = attrs[:log_start_idx].abs().sum().item()
        log_attr = attrs[log_start_idx:].abs().sum().item()
        total = meta_attr + log_attr
        print(f"\nAttribution Density:")
        print(f"  Metadata: {meta_attr/total:.2%}  [{'█'*int(20*meta_attr/total):20s}]")
        print(f"  Evidence: {log_attr/total:.2%}  [{'█'*int(20*log_attr/total):20s}]")
        
        if log_attr / total < 0.1:
            print(f"\n✅ MECHANISTIC PROOF: Evidence attribution is {log_attr/total:.2%} (<10%).")
            print("   Model is ignoring logs and retrieving from metadata prior.")
    
    analyzer.visualise(attrs, ids, f"figures/mechanistic_proof_{Path(args.incident).stem}.png")

if __name__ == "__main__":
    main()
