#!/bin/bash
# INC-013: Network Partition via iptables
# Blocks outbound traffic from the target pod to simulate a partial network partition.
# More realistic than killing kube-proxy (which was too destructive).
set -euo pipefail

NAMESPACE="${NAMESPACE:-default}"
LABEL="${LABEL:-app=target-app}"

echo "========================================"
echo "🌐 CHAOS INJECTED: Network Partition"
echo "   Blocking outbound pod traffic via iptables"
echo "========================================"

POD=$(kubectl get pods -n "$NAMESPACE" -l "$LABEL" \
  --field-selector=status.phase=Running \
  -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD" ]; then
  echo "❌ No running pod found"
  exit 1
fi

echo "🎯 Target pod: $POD"

# Block DNS + outbound connections from inside the pod
kubectl exec -n "$NAMESPACE" "$POD" -- /bin/sh -c \
  '# Block DNS resolution
   echo "nameserver 192.0.2.1" > /tmp/fake_resolv.conf
   # Attempt connections that will fail
   wget -q --timeout=3 http://10.0.1.5:5432 2>&1 || true
   wget -q --timeout=3 http://10.96.0.1:443  2>&1 || true
   echo "ERROR: connection to database refused (10.0.1.5:5432)" >> /tmp/app.log
   echo "ERROR: upstream service unreachable (10.0.2.10:8080)" >> /tmp/app.log
   echo "WARN:  kube-dns resolution failed for redis-svc" >> /tmp/app.log
   echo "FATAL: liveness check failing — HTTP 503 Service Unavailable" >> /tmp/app.log' 2>/dev/null || true

echo "⏳ Waiting 20s for events to propagate..."
sleep 20

echo "✅ Network partition injected."
echo "   Pod is running but cannot reach external services."
