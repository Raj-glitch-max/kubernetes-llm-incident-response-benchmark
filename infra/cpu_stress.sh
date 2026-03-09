#!/bin/bash
# CPU Stress — runs a tight infinite loop in the target-app container to max out CPU
set -euo pipefail
echo "[chaos] Injecting CPU stress on target-app..."
POD=$(kubectl get pods -n default -l app=target-app -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n default "$POD" -- /bin/sh -c "yes > /dev/null &" > /dev/null 2>&1 < /dev/null &
echo "[chaos] CPU stress started in pod: $POD"
echo "[chaos] Waiting 60s for Prometheus to fire HighCpuUsage alert..."
sleep 60
echo "[chaos] CPU stress injected."
