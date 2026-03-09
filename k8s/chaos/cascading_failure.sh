#!/bin/bash
# INC-011: Cascading Failure — pod_kill + cpu_stress simultaneously
# This is the scenario nobody benchmarks: two simultaneous failures.
# The LLM must identify BOTH causes, not just one.
set -euo pipefail

NAMESPACE="${NAMESPACE:-default}"
LABEL="${LABEL:-app=target-app}"

echo "========================================"
echo "💥 CHAOS INJECTED: Cascading Failure"
echo "   pod_kill + cpu_stress simultaneously"
echo "========================================"

# Get all ready pods
PODS=($(kubectl get pods -n "$NAMESPACE" -l "$LABEL" \
  --field-selector=status.phase=Running \
  -o jsonpath='{.items[*].metadata.name}'))

if [ ${#PODS[@]} -lt 2 ]; then
  echo "❌ Need at least 2 running pods for cascading failure. Found: ${#PODS[@]}"
  exit 1
fi

VICTIM="${PODS[0]}"
CPU_TARGET="${PODS[1]}"

echo "🔪 Killing pod: $VICTIM"
kubectl delete pod "$VICTIM" -n "$NAMESPACE" --grace-period=0 &

echo "🔥 Injecting CPU stress on: $CPU_TARGET"
kubectl exec -n "$NAMESPACE" "$CPU_TARGET" -- /bin/sh -c "yes > /dev/null & yes > /dev/null &" 2>/dev/null &

echo "⏳ Waiting 30s for both chaos events to register in events..."
sleep 30

echo "✅ Cascading chaos complete — both pod_kill + cpu_stress active"
echo "   A good LLM should cite BOTH causes in its RCA."
