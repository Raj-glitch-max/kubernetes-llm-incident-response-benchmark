#!/bin/bash
# Memory Hog — allocates memory in target container until OOMKilled
set -euo pipefail
echo "[chaos] Injecting memory hog in target-app..."
POD=$(kubectl get pods -n default -l app=target-app -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n default "$POD" -- /bin/sh -c "cat /dev/zero | grep -a 'impossible_string' 2>/dev/null &" &
echo "[chaos] Memory hog started in pod: $POD"
echo "[chaos] Waiting 60s for OOMKilled event..."
sleep 60
echo "[chaos] Memory hog injected."
