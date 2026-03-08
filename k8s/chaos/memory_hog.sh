#!/bin/bash
# Memory Hog — allocates memory in target container until OOMKilled
set -euo pipefail
echo "[chaos] Injecting memory hog in target-app..."
POD=$(kubectl get pods -n default -l app=target-app -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n default "$POD" -- /bin/sh -c "
  python3 -c \"
import subprocess
data = []
while True:
    data.append(' ' * 1024 * 1024 * 10)  # 10MB chunks
\" 2>&1 &" &
echo "[chaos] Memory hog started in pod: $POD"
echo "[chaos] Waiting 60s for OOMKilled event..."
sleep 60
echo "[chaos] Memory hog injected."
