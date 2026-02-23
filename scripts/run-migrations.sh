#!/bin/bash
set -e

# CV-Tailor Database Migration Script
# Runs Django migrations on ECS task

# Load shared configuration
SCRIPT_DIR="$(dirname "$0")"
source "${SCRIPT_DIR}/config.sh"

echo "============================================"
echo "CV-Tailor Database Migrations"
echo "============================================"
echo ""

# Get running task
echo "Finding running task..."
TASK_ARN=$(aws ecs list-tasks \
  --cluster ${CLUSTER_NAME} \
  --service-name ${SERVICE_NAME} \
  --desired-status RUNNING \
  --region ${AWS_REGION} \
  --query 'taskArns[0]' \
  --output text)

if [ "$TASK_ARN" == "None" ] || [ -z "$TASK_ARN" ]; then
  echo "❌ Error: No running tasks found"
  echo ""
  echo "Please ensure:"
  echo "1. Backend deployment completed successfully"
  echo "2. ECS service has at least one running task"
  echo ""
  echo "Check status with: ./scripts/check-health.sh"
  exit 1
fi

TASK_ID=$(basename $TASK_ARN)
echo "  Task ID: ${TASK_ID}"
echo ""

# Run migrations
echo "Running migrations..."
echo "  Command: uv run python manage.py migrate"
echo ""

aws ecs execute-command \
  --cluster ${CLUSTER_NAME} \
  --task ${TASK_ID} \
  --container app \
  --command "uv run python manage.py migrate" \
  --interactive \
  --region ${AWS_REGION}

echo ""
echo "✅ Migrations complete!"
echo ""

# Optionally create superuser
read -p "Would you like to create a superuser? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo ""
  echo "Creating superuser..."
  aws ecs execute-command \
    --cluster ${CLUSTER_NAME} \
    --task ${TASK_ID} \
    --container app \
    --command "uv run python manage.py createsuperuser" \
    --interactive \
    --region ${AWS_REGION}
fi

echo ""
echo "🎉 Database setup complete!"
echo ""
