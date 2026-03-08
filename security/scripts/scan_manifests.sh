#!/bin/bash
# Runs checkov on k8s/ directory
mkdir -p security/reports
checkov -d k8s/ -o json > security/reports/checkov_report.json
echo "checkov scan complete."
