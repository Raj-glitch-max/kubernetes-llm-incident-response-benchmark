#!/bin/bash
# k8s/chaos/pod_kill.sh
# Purpose: Randomly kills one pod in the target-app deployment
# Useful for testing if the ReplicaSet correctly spins up a replacement.

echo "========================================"
echo "💀 CHAOS INJECTED: Pod Kill (Random)"
echo "========================================"

# Step 1: Find all pods belonging to our target app.
# -n default: Looks only in the 'default' namespace
# -l app=target-app: Filters pods that have this specific label
# -o name: Outputs ONLY the name of the pod (e.g., pod/target-app-12345), ignoring the headers and status columns.
echo "🔍 Scanning for target-app pods..."
ALL_PODS=$(kubectl get pods -n default -l app=target-app -o name)

# Check if any pods were actually found. (-z checks if the string is empty)
if [ -z "$ALL_PODS" ]; then
    echo "❌ Error: No pods found with label app=target-app in the default namespace."
    exit 1
fi

# Step 2: Pick one random pod to be our victim.
# Command substitution $(...) runs the code inside and captures its output.
# We echo the list of all pods, and pipe (|) it into `shuf`
# `shuf -n 1` shuffles the lines randomly and outputs exactly 1 line.
VICTIM_POD=$(echo "$ALL_PODS" | shuf -n 1)

echo "🎯 Selected victim: $VICTIM_POD"

# Step 3: Execute the kill order.
# We pass the exact pod string (pod/target-app-xyz) directly to kubectl delete.
echo "🔪 Terminating pod..."
kubectl delete -n default "$VICTIM_POD"

echo "✅ Chaos execution complete. Run 'kubectl get pods' to watch it recover."
