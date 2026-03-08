#!/bin/bash
# k8s/chaos/crash_loop.sh
# Purpose: Triggers a CrashLoopBackOff across the deployment by setting a fake image

echo "========================================"
echo "💀 CHAOS INJECTED: CrashLoopBackOff"
echo "========================================"

echo "🚀 Injecting fake image tag to force ImagePullBackOff / CrashLoopBackOff..."
kubectl set image deployment/target-app target-app=nginx:this-tag-is-fake-123 -n default

echo "✅ Chaos execution complete. Deploying bad image..."
echo "Watch it break: kubectl get pods -n default -w"
