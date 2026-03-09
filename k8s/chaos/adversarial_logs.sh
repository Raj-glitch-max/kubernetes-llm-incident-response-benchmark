#!/bin/bash
# Adversarial Logs — The "Holy Shit" Scenario
# Injects an OOM kill but plants misleading healthy-looking log entries
# BEFORE capturing so the LLM has to distinguish signal from noise.
# No open benchmark tests this. This is novel.
set -euo pipefail

echo "========================================"
echo "🧪 CHAOS INJECTED: Adversarial Log Injection"
echo "========================================"
echo "🎭 Strategy: OOM kill hidden behind misleading healthy log noise"

NAMESPACE="${NAMESPACE:-default}"
LABEL="${LABEL:-app=target-app}"

# Step 1: Select a running pod
POD=$(kubectl get pods -n "$NAMESPACE" -l "$LABEL" \
  --field-selector=status.phase=Running \
  -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

if [ -z "$POD" ]; then
  echo "❌ No running pod found for label $LABEL"
  exit 1
fi

echo "🎯 Target pod: $POD"

# Step 2: Write decoy healthy log messages into a temp file that
#         capture_incident.sh will pick up (we abuse a sidecar pattern
#         by writing to /dev/termination-log which kubectl logs will surface)
echo "🪤 Planting decoy messages in pod logs..."
kubectl exec -n "$NAMESPACE" "$POD" -- /bin/sh -c \
  'echo "INFO: All systems healthy. No errors detected." >> /tmp/app.log; \
   echo "INFO: Database connection stable on 10.0.1.5:5432" >> /tmp/app.log; \
   echo "INFO: Memory usage nominal: 45Mi / 128Mi" >> /tmp/app.log; \
   echo "INFO: Liveness probe passing. Uptime: 14m32s" >> /tmp/app.log' \
  2>/dev/null || true

sleep 2

# Step 3: Now OOM-kill it — the REAL story is buried under the noise
echo "💣 Triggering real OOM kill (the hidden signal)..."
kubectl exec -n "$NAMESPACE" "$POD" -- /bin/sh -c \
  "cat /dev/zero | head -c 200m > /dev/null 2>&1 &" \
  2>/dev/null || true

echo "⏳ Waiting 15s for kernel OOM killer to fire..."
sleep 15

echo "✅ Adversarial chaos injected."
echo "   LLM must detect OOMKilled despite healthy-looking log noise."
echo "   Run 'kubectl get pods' to verify pod restarted."
