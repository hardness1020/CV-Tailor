#!/bin/bash

# CV-Tailor Health Check Script
# Verifies deployment status

# Load shared configuration
SCRIPT_DIR="$(dirname "$0")"
source "${SCRIPT_DIR}/config.sh"

echo "============================================"
echo "CV-Tailor Deployment Health Check"
echo "============================================"
echo ""

# Check ECS Service
echo "1. ECS Service Status"
echo "   ==================="
SERVICE_INFO=$(aws ecs describe-services \
  --cluster ${CLUSTER_NAME} \
  --services ${SERVICE_NAME} \
  --region ${AWS_REGION} \
  --query 'services[0]' \
  --output json)

RUNNING_COUNT=$(echo $SERVICE_INFO | jq -r '.runningCount')
DESIRED_COUNT=$(echo $SERVICE_INFO | jq -r '.desiredCount')
PENDING_COUNT=$(echo $SERVICE_INFO | jq -r '.pendingCount')

echo "   Desired tasks: ${DESIRED_COUNT}"
echo "   Running tasks: ${RUNNING_COUNT}"
echo "   Pending tasks: ${PENDING_COUNT}"

if [ "$RUNNING_COUNT" -eq "$DESIRED_COUNT" ] && [ "$RUNNING_COUNT" -gt 0 ]; then
  echo "   ✅ Service healthy"
else
  echo "   ⚠️  Service not fully healthy"
fi
echo ""

# Check Task Health
echo "2. Task Details"
echo "   ============"
TASK_ARNS=$(aws ecs list-tasks \
  --cluster ${CLUSTER_NAME} \
  --service-name ${SERVICE_NAME} \
  --region ${AWS_REGION} \
  --query 'taskArns' \
  --output text)

if [ -z "$TASK_ARNS" ]; then
  echo "   ❌ No tasks found"
  echo ""
  echo "   Troubleshooting:"
  echo "   - Check ECS service events for errors"
  echo "   - View logs: ./scripts/view-logs.sh"
  echo "   - Verify Docker image exists in ECR"
else
  for TASK_ARN in $TASK_ARNS; do
    TASK_ID=$(basename $TASK_ARN)
    TASK_INFO=$(aws ecs describe-tasks \
      --cluster ${CLUSTER_NAME} \
      --tasks ${TASK_ARN} \
      --region ${AWS_REGION} \
      --query 'tasks[0]' \
      --output json)

    TASK_STATUS=$(echo $TASK_INFO | jq -r '.lastStatus')
    HEALTH_STATUS=$(echo $TASK_INFO | jq -r '.healthStatus // "UNKNOWN"')

    echo "   Task: ${TASK_ID}"
    echo "     Status: ${TASK_STATUS}"
    echo "     Health: ${HEALTH_STATUS}"
  done
  echo "   ✅ Tasks found"
fi
echo ""

# Check ALB Target Health
echo "3. Load Balancer Health"
echo "   ===================="
# Get target group ARN from Terraform state
cd terraform
TARGET_GROUP_ARN=$(terraform output -raw alb_target_group_arn 2>/dev/null || echo "")
cd ..

if [ -z "$TARGET_GROUP_ARN" ]; then
  echo "   ⚠️  Could not get target group ARN"
else
  TARGET_HEALTH=$(aws elbv2 describe-target-health \
    --target-group-arn ${TARGET_GROUP_ARN} \
    --region ${AWS_REGION} \
    --output json)

  HEALTHY_COUNT=$(echo $TARGET_HEALTH | jq '[.TargetHealthDescriptions[] | select(.TargetHealth.State == "healthy")] | length')
  TOTAL_COUNT=$(echo $TARGET_HEALTH | jq '.TargetHealthDescriptions | length')

  echo "   Healthy targets: ${HEALTHY_COUNT}/${TOTAL_COUNT}"

  if [ "$HEALTHY_COUNT" -gt 0 ]; then
    echo "   ✅ At least one healthy target"
  else
    echo "   ❌ No healthy targets"
    echo ""
    echo "   Target details:"
    echo $TARGET_HEALTH | jq -r '.TargetHealthDescriptions[] | "     - \(.Target.Id): \(.TargetHealth.State) (\(.TargetHealth.Description // "no description"))"'
  fi
fi
echo ""

# Check Backend API
echo "4. Backend API Health"
echo "   ==================="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" ${API_URL}/health/ 2>/dev/null || echo "000")

if [ "$HTTP_CODE" == "200" ]; then
  echo "   ✅ Backend API responding (HTTP ${HTTP_CODE})"
  echo "   URL: ${API_URL}/health/"
else
  echo "   ❌ Backend API not responding (HTTP ${HTTP_CODE})"
  echo "   URL: ${API_URL}/health/"
fi
echo ""

# Check Frontend
echo "5. Frontend Availability"
echo "   ====================="
FRONTEND_CODE=$(curl -s -o /dev/null -w "%{http_code}" ${FRONTEND_URL} 2>/dev/null || echo "000")

if [ "$FRONTEND_CODE" == "200" ]; then
  echo "   ✅ Frontend responding (HTTP ${FRONTEND_CODE})"
  echo "   URL: ${FRONTEND_URL}"
else
  echo "   ⚠️  Frontend not responding (HTTP ${FRONTEND_CODE})"
  echo "   URL: ${FRONTEND_URL}"
fi
echo ""

# Summary
echo "============================================"
echo "Summary"
echo "============================================"
echo ""
echo "Backend API:  ${API_URL}"
echo "Frontend:     ${FRONTEND_URL}"
echo ""

if [ "$HTTP_CODE" == "200" ] && [ "$RUNNING_COUNT" -gt 0 ]; then
  echo "✅ Application appears healthy!"
else
  echo "⚠️  Some issues detected. See details above."
  echo ""
  echo "Troubleshooting commands:"
  echo "  ./scripts/view-logs.sh     - View application logs"
  echo "  ./scripts/run-migrations.sh - Run database migrations"
fi
echo ""
