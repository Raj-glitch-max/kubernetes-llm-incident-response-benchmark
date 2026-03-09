#!/bin/bash
# k8s/chaos/oom_kill.sh
# Purpose: Force an OOMKilled event on a specific pod using a memory stress tool
# This uses 'kubectl exec' to run a dd command that eats memory instantly.

echo "========================================"
echo "💀 CHAOS INJECTED: Pod OOMKilled"
echo "========================================"

# Find a random pod
ALL_PODS=$(kubectl get pods -n default -l app=target-app -o name)

if [ -z "$ALL_PODS" ]; then
    echo "❌ Error: No target-app pods found."
    exit 1
fi

VICTIM_POD=$(echo "$ALL_PODS" | shuf -n 1)
# Clean 'pod/' prefix for exec
POD_NAME=$(echo "$VICTIM_POD" | cut -d '/' -f2)

echo "🎯 Selected victim: $POD_NAME"
echo "💣 Forcing memory spike to trigger kernel OOM Killer..."

# Our pod is limited to 128Mi. This dd command tries to write 500MB to /dev/null
# directly from /dev/zero, fully in memory, instantly bypassing the limit.
# The kernel will immediately terminate it with Exit Code 137 (OOMKilled).
kubectl exec -n default "$POD_NAME" -- dd if=/dev/zero of=/dev/null bs=500M count=1 &>/dev/null &

echo "✅ Chaos execution complete. The pod should be OOMKilled within seconds."
