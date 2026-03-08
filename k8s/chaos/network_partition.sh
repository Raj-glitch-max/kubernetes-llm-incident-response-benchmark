#!/bin/bash
# Network Partition — kills all kube-proxy pods to simulate network failure
set -euo pipefail
echo "[chaos] Injecting network partition: killing kube-proxy pods..."
kubectl delete pods -n kube-system -l k8s-app=kube-proxy --grace-period=0 --force
echo "[chaos] Waiting 30s for Prometheus to fire NetworkFailure alert..."
sleep 30
echo "[chaos] Network partition injected."
