#!/bin/bash
# Runs tfsec on terraform/ directory, outputs to security/reports/
mkdir -p security/reports
tfsec terraform/ --format json --out security/reports/tfsec_report.json
echo "tfsec scan complete."
