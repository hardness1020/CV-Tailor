#!/bin/bash
# CV Tailor Production Restart Script
# Restarts AWS production infrastructure after shutdown
# Last updated: 2025-10-24

set -e

# Load shared configuration
SCRIPT_DIR="$(dirname "$0")"
source "${SCRIPT_DIR}/config.sh"

# Use config variables
REGION="${AWS_REGION}"
CLUSTER="${CLUSTER_NAME}"
SERVICE="${SERVICE_NAME}"

echo "======================================"
echo "CV Tailor Production Restart"
echo "======================================"
echo ""
echo "This script will attempt to restart production services."
echo ""

# Check what's currently running
echo "Checking current infrastructure status..."
echo ""

# Check ECS
echo "[1/4] Checking ECS service..."
ECS_STATUS=$(aws ecs describe-services \
  --cluster $CLUSTER \
  --services $SERVICE \
  --region $REGION \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}' \
  --output table 2>/dev/null) || ECS_STATUS="NOT FOUND"

if [ "$ECS_STATUS" != "NOT FOUND" ]; then
  echo "$ECS_STATUS"
  RUNNING_COUNT=$(aws ecs describe-services \
    --cluster $CLUSTER \
    --services $SERVICE \
    --region $REGION \
    --query 'services[0].runningCount' \
    --output text)
else
  echo "ECS service not found - needs recreation"
  RUNNING_COUNT=0
fi
echo ""

# Check RDS
echo "[2/4] Checking RDS database..."
RDS_STATUS=$(aws rds describe-db-instances \
  --db-instance-identifier $DB_INSTANCE \
  --region $REGION \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Endpoint:Endpoint.Address}' \
  --output table 2>/dev/null) || RDS_STATUS="NOT FOUND"

if [ "$RDS_STATUS" != "NOT FOUND" ]; then
  echo "$RDS_STATUS"
  DB_STATE=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE \
    --region $REGION \
    --query 'DBInstances[0].DBInstanceStatus' \
    --output text)
else
  echo "RDS database not found - needs recreation"
  DB_STATE="not-found"
fi
echo ""

# Check ALB
echo "[3/4] Checking Application Load Balancer..."
ALB_STATUS=$(aws elbv2 describe-load-balancers \
  --names ${ALB_NAME} \
  --region $REGION \
  --query 'LoadBalancers[0].{DNSName:DNSName,State:State.Code}' \
  --output table 2>/dev/null) || ALB_STATUS="NOT FOUND"

if [ "$ALB_STATUS" != "NOT FOUND" ]; then
  echo "$ALB_STATUS"
  ALB_EXISTS="yes"
else
  echo "ALB not found - needs recreation"
  ALB_EXISTS="no"
fi
echo ""

# Check Redis
echo "[4/4] Checking ElastiCache Redis..."
REDIS_STATUS=$(aws elasticache describe-replication-groups \
  --replication-group-id ${REDIS_GROUP} \
  --region $REGION \
  --query 'ReplicationGroups[0].{Status:Status,Endpoint:NodeGroups[0].PrimaryEndpoint.Address}' \
  --output table 2>/dev/null) || REDIS_STATUS="NOT FOUND"

if [ "$REDIS_STATUS" != "NOT FOUND" ]; then
  echo "$REDIS_STATUS"
  REDIS_EXISTS="yes"
else
  echo "Redis not found - needs recreation"
  REDIS_EXISTS="no"
fi
echo ""

echo "======================================"
echo "Restart Strategy"
echo "======================================"
echo ""

# Determine restart strategy
if [ "$RDS_STATUS" = "NOT FOUND" ] || [ "$REDIS_STATUS" = "NOT FOUND" ] || [ "$ALB_STATUS" = "NOT FOUND" ]; then
  echo "⚠️  FULL RESTART REQUIRED"
  echo ""
  echo "Missing critical infrastructure. This requires manual recreation:"
  echo ""
  if [ "$RDS_STATUS" = "NOT FOUND" ]; then
    echo "  ❌ RDS Database - See docs/deployment/restart-guide.md (Phase 1)"
  fi
  if [ "$REDIS_STATUS" = "NOT FOUND" ]; then
    echo "  ❌ ElastiCache Redis - See docs/deployment/restart-guide.md (Phase 2)"
  fi
  if [ "$ALB_STATUS" = "NOT FOUND" ]; then
    echo "  ❌ Application Load Balancer - See docs/deployment/restart-guide.md (Phase 3)"
  fi
  echo ""
  echo "Please follow the manual restart guide at:"
  echo "  docs/deployment/restart-guide.md"
  echo ""
  echo "Estimated time: 30-60 minutes"
  exit 1
fi

# Quick restart path
echo "✅ QUICK RESTART AVAILABLE"
echo ""
echo "All infrastructure exists. Performing quick restart..."
echo ""

read -p "Continue with restart? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Restart cancelled."
  exit 0
fi

echo ""

# Start RDS if stopped
if [ "$DB_STATE" = "stopped" ]; then
  echo "[1/2] Starting RDS database..."
  aws rds start-db-instance \
    --db-instance-identifier $DB_INSTANCE \
    --region $REGION

  echo "Waiting for RDS to be available (may take 5-10 minutes)..."
  aws rds wait db-instance-available \
    --db-instance-identifier $DB_INSTANCE \
    --region $REGION
  echo "✓ RDS is now available"
  echo ""
elif [ "$DB_STATE" = "available" ]; then
  echo "[1/2] RDS database already running"
  echo ""
else
  echo "[1/2] RDS in state: $DB_STATE"
  echo "Waiting for RDS to be available..."
  aws rds wait db-instance-available \
    --db-instance-identifier $DB_INSTANCE \
    --region $REGION
  echo "✓ RDS is now available"
  echo ""
fi

# Scale ECS service
if [ "$RUNNING_COUNT" -lt 2 ]; then
  echo "[2/2] Scaling ECS service to 2 tasks..."
  aws ecs update-service \
    --cluster $CLUSTER \
    --service $SERVICE \
    --desired-count 2 \
    --region $REGION \
    --query 'service.{Name:serviceName,DesiredCount:desiredCount,RunningCount:runningCount}' \
    --output table

  echo ""
  echo "Waiting for tasks to start (grace period: 180 seconds)..."
  echo "This may take 3-5 minutes..."

  # Wait for tasks to be running
  for i in {1..20}; do
    sleep 15
    RUNNING=$(aws ecs describe-services \
      --cluster $CLUSTER \
      --services $SERVICE \
      --region $REGION \
      --query 'services[0].runningCount' \
      --output text)

    echo "  Running tasks: $RUNNING/2 (check $i/20)"

    if [ "$RUNNING" = "2" ]; then
      echo "✓ All tasks running!"
      break
    fi
  done
  echo ""
else
  echo "[2/2] ECS service already running with $RUNNING_COUNT tasks"
  echo ""
fi

echo "======================================"
echo "Restart Complete!"
echo "======================================"
echo ""

# Verify health
echo "Verifying backend health..."
sleep 10

HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" ${API_URL}/health/ 2>/dev/null || echo "000")

if [ "$HEALTH_CHECK" = "200" ]; then
  echo "✅ Backend health check PASSED (HTTP 200)"
else
  echo "⚠️  Backend health check returned HTTP $HEALTH_CHECK"
  echo "   This is normal if tasks just started. Wait 2-3 minutes and try:"
  echo "   curl ${API_URL}/health/"
fi

echo ""
echo "Frontend: ${FRONTEND_URL}"
echo "Backend:  ${API_URL}"
echo ""
echo "To monitor ECS deployment:"
echo "  aws ecs describe-services --cluster $CLUSTER --service $SERVICE --region $REGION"
echo ""
echo "To view logs:"
echo "  aws logs tail ${LOG_GROUP} --since 5m --region $REGION --follow"
echo ""
