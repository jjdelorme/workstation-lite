#!/bin/bash
# Magic Connect Script for Workstation Lite
set -e

echo "Configuring connection to your workstation openvs-workstation..."
gcloud config set project jasondel-cloudrun10 --quiet
# We use ADC token to avoid kubectl plugin requirements
TOKEN=$(gcloud auth application-default print-access-token)
ENDPOINT=$(gcloud container clusters describe workstation-cluster --region us-central1 --format="value(endpoint)")

# Setup temp bin for kubectl if needed
TEMP_BIN_DIR="/tmp/workstation-bin"
mkdir -p $TEMP_BIN_DIR
export PATH="$TEMP_BIN_DIR:$PATH"

if ! command -v kubectl &> /dev/null; then
    echo "kubectl not found, downloading standalone binary..."
    curl -s -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    chmod +x kubectl
    mv kubectl $TEMP_BIN_DIR/
fi

echo "Starting port-forwarding (3000) and launching terminal..."
# Kill any existing port-forward to 3000
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

# Start port-forward in background using token-based auth to bypass plugin
# REDIRECTED OUTPUT TO /dev/null TO HIDE "Handling connection" MESSAGES
kubectl --token="$TOKEN" --server="https://$ENDPOINT" --insecure-skip-tls-verify port-forward pod/openvs-workstation-0 3000:3000 -n user-1 > /dev/null 2>&1 &
PF_PID=$!

# Trap exit to kill port-forward
trap "kill $PF_PID" EXIT

# Wait for port-forward
sleep 2

echo "Connecting to shell..."
# Try ZSH first (custom image), fallback to BASH
if kubectl --token="$TOKEN" --server="https://$ENDPOINT" --insecure-skip-tls-verify exec pod/openvs-workstation-0 -n user-1 -- which zsh &>/dev/null; then
    SHELL_BIN="/bin/zsh"
else
    SHELL_BIN="/bin/bash"
fi

kubectl --token="$TOKEN" --server="https://$ENDPOINT" --insecure-skip-tls-verify exec -it pod/openvs-workstation-0 -n user-1 -- $SHELL_BIN < /dev/tty