#!/bin/bash
# capture_incident.sh
# Collects evidence for the LLM pipeline post-chaos.

INCIDENT_ID=$1
CHAOS_TYPE=$2
GROUND_TRUTH=$3

if [ -z "$INCIDENT_ID" ] || [ -z "$CHAOS_TYPE" ] || [ -z "$GROUND_TRUTH" ]; then
    echo "Usage: ./capture_incident.sh <INC-XXX> <ChaosType> <GroundTruthCategory>"
    echo "Example: ./capture_incident.sh INC-001 pod_kill_random PodCrashLooping"
    exit 1
fi

OUT_DIR="data/raw_logs/${INCIDENT_ID}"
mkdir -p "$OUT_DIR"

echo "📸 Capturing incident evidence into ${OUT_DIR}..."

# 1. Metadata (Setting Ground Truth BEFORE LLM is called)
cat <<EOF > "${OUT_DIR}/metadata.json"
{
  "incident_id": "${INCIDENT_ID}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "chaos_type": "${CHAOS_TYPE}",
  "ground_truth_category": "${GROUND_TRUTH}"
}
EOF

# 2. Events stream
kubectl get events -n default --sort-by=.lastTimestamp > "${OUT_DIR}/events.txt"

# 3. Pod logs (We pick one failed or struggling pod)
TARGET_POD=$(kubectl get pods -n default -l app=target-app --sort-by=.status.startTime | tail -n 1 | awk '{print $1}')
kubectl logs "$TARGET_POD" -n default --tail=200 > "${OUT_DIR}/pod_logs.txt" || echo "Could not fetch logs" > "${OUT_DIR}/pod_logs.txt"

# 4. Describe Output
kubectl describe pod "$TARGET_POD" -n default > "${OUT_DIR}/describe_output.txt"

echo "✅ Capture complete for ${INCIDENT_ID}!"
