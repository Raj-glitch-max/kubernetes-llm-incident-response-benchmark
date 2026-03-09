import subprocess
import json
import time
import csv
from pathlib import Path

def run_command(cmd, cwd="."):
    print(f"Executing: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing command: {cmd}")
        print(f"Stderr: {result.stderr}")
    return result.stdout

def get_metadata(incident_id):
    meta_path = Path(f"data/raw_logs/{incident_id}/metadata.json")
    if meta_path.exists():
        with open(meta_path) as f:
            return json.load(f)
    return {"chaos_type": "pod_kill", "ground_truth_category": "PodCrashLooping"}

def load_evaluated_pairs():
    csv_path = Path("data/incidents.csv")
    if not csv_path.exists():
        return set()
    
    # Model aliases to canonical names
    aliases = {
        "nvidia-glm47": "z-ai/glm4.7",
        "nvidia-llama": "meta/llama-3.1-70b-instruct",
        "nvidia-mistral": "mistralai/mistral-7b-instruct-v0.3",
        "z-ai/glm4.7": "nvidia-glm47",
        "meta/llama-3.1-70b-instruct": "nvidia-llama",
        "mistralai/mistral-7b-instruct-v0.3": "nvidia-mistral"
    }

    pairs = set()
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            inc = row["incident_id"]
            mod = row["model"]
            pairs.add((inc, mod))
            # Also add the alias if it exists to be safe
            if mod in aliases:
                pairs.add((inc, aliases[mod]))
    return pairs

def main():
    evaluated = load_evaluated_pairs()
    print(f"Loaded {len(evaluated)} already evaluated incident-model pairs.")

    # Step 3: Real runs
    models_step3 = [
        "nvidia-glm47", "nvidia-llama", "nvidia-mistral",
        "meta/llama-3.3-70b-instruct",
        "nvidia/mistral-nemo-minitron-8b-8k-instruct"
    ]
    
    incidents_step3 = [f"INC-{i:03d}" for i in range(16)]
    
    print("--- Starting Step 3: Real runs ---")
    for inc in incidents_step3:
        all_done = True
        for model in models_step3:
            if (inc, model) not in evaluated:
                all_done = False
                break
        
        if all_done:
            print(f"Skipping incident {inc} - all models already evaluated.")
            continue

        meta = get_metadata(inc)
        scenario = meta.get("chaos_type", "pod_kill")
        category = meta.get("ground_truth_category", "PodCrashLooping")
        
        # Check if raw logs exist to skip setup
        log_dir = Path(f"data/raw_logs/{inc}")
        if log_dir.exists() and (log_dir / "metadata.json").exists() and (log_dir / "pod_logs.txt").exists():
            print(f"Incident {inc} raw logs already exist. Skipping chaos/capture.")
        else:
            print(f"Incident: {inc}, Scenario: {scenario}, Category: {category}")
            # Run chaos and capture once per incident
            run_command(f"make chaos SCENARIO={scenario}")
            run_command(f"make capture INCIDENT={inc} SCENARIO={scenario} CATEGORY={category}")
        
        for model in models_step3:
            if (inc, model) in evaluated:
                print(f"  Skipping model {model} for {inc} - already done.")
                continue
            run_command(f"make eval INCIDENT={inc} MODEL={model}")
            time.sleep(1)

    # Step 4: Ablation runs
    # (Ablation and RLHF results usually go to different files, so check those too if needed, 
    # but for now let's just run them as requested or check their output files)
    print("--- Starting Step 4: Ablation runs ---")
    ablation_incidents = ["INC-002", "INC-003", "INC-007", "INC-008", "INC-013"]
    ablation_models = ["nvidia-llama", "nvidia-mistral", "nvidia-glm47"]
    ablation_conditions = ["A", "B", "C", "D"]
    
    ablation_results_path = Path("data/ablation_results.csv")
    evaluated_ablation = set()
    if ablation_results_path.exists():
        with open(ablation_results_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                evaluated_ablation.add((row["incident_id"], row["model"], row["condition"]))

    for inc in ablation_incidents:
        for cond in ablation_conditions:
            for model in ablation_models:
                if (inc, model, cond) in evaluated_ablation:
                    print(f"Skipping ablation {inc} {model} {cond} - already done.")
                    continue
                run_command(f"python3 eval/ablation.py --incident {inc} --condition {cond} --model {model}")

    # Step 5: RLHF test
    print("--- Starting Step 5: RLHF test ---")
    rlhf_incidents = ["INC-002", "INC-003", "INC-007", "INC-008", "INC-013"]
    instruct_model = "nvidia/mistral-nemo-minitron-8b-8k-instruct"
    base_model = "nvidia/mistral-nemo-minitron-8b-base"
    
    rlhf_results_path = Path("data/rlhf_test_results.csv")
    evaluated_rlhf = set()
    if rlhf_results_path.exists():
        with open(rlhf_results_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                evaluated_rlhf.add((row["incident_id"], row["model_slug"]))

    for inc in rlhf_incidents:
        if (inc, instruct_model) in evaluated_rlhf and (inc, base_model) in evaluated_rlhf:
            print(f"Skipping RLHF test for {inc} - already done.")
            continue
        run_command(f"python3 eval/rlhf_test.py --incident {inc} --instruct {instruct_model} --base {base_model}")

    # Step 6: Leaderboard
    print("--- Starting Step 6: Regenerate leaderboard ---")
    run_command("make leaderboard")
    run_command("python3 eval/confident_liar.py")

    print("\n✅ All steps completed!")

if __name__ == "__main__":
    main()
