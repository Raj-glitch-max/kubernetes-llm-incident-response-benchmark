#!/bin/bash
# Runs trivy on images defined in k8s/apps/ manifests
mkdir -p security/reports
trivy config k8s/apps/ --format json --output security/reports/trivy_report.json
echo "trivy scan complete."
