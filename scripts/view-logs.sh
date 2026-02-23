#!/bin/bash

# CV-Tailor Log Viewer Script
# Streams logs from ECS tasks

# Load shared configuration
SCRIPT_DIR="$(dirname "$0")"
source "${SCRIPT_DIR}/config.sh"

echo "============================================"
echo "CV-Tailor Application Logs"
echo "============================================"
echo ""

# Menu
echo "Select log view:"
echo "  1) Tail logs (follow mode)"
echo "  2) Last 100 lines"
echo "  3) Last 1 hour"
echo "  4) Search for errors"
echo ""
read -p "Choose option (1-4): " -n 1 -r
echo ""
echo ""

case $REPLY in
  1)
    echo "Tailing logs (Ctrl+C to exit)..."
    echo ""
    aws logs tail ${LOG_GROUP} \
      --follow \
      --region ${AWS_REGION} \
      --format short
    ;;
  2)
    echo "Last 100 lines:"
    echo ""
    aws logs tail ${LOG_GROUP} \
      --region ${AWS_REGION} \
      --format short \
      | tail -100
    ;;
  3)
    echo "Last 1 hour:"
    echo ""
    aws logs tail ${LOG_GROUP} \
      --since 1h \
      --region ${AWS_REGION} \
      --format short
    ;;
  4)
    echo "Searching for errors (last 1 hour)..."
    echo ""
    aws logs tail ${LOG_GROUP} \
      --since 1h \
      --filter-pattern "ERROR" \
      --region ${AWS_REGION} \
      --format short
    ;;
  *)
    echo "Invalid option. Showing last 100 lines:"
    echo ""
    aws logs tail ${LOG_GROUP} \
      --region ${AWS_REGION} \
      --format short \
      | tail -100
    ;;
esac

echo ""
