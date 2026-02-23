#!/bin/bash
# CV Tailor Production Shutdown Script
# Shuts down all AWS production infrastructure to minimize costs
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
echo "CV Tailor Production Shutdown"
echo "======================================"
echo ""
echo "This will shut down:"
echo "  - ECS Backend (scale to 0)"
echo "  - RDS PostgreSQL (delete, no snapshot - no user data)"
echo "  - ElastiCache Redis (delete)"
echo "  - Application Load Balancer"
echo "  - Target Group"
echo ""
echo "Monthly savings: ~$120-150"
echo ""
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Shutdown cancelled."
  exit 0
fi

echo ""
echo "Starting shutdown process..."
echo ""

# 1. Stop ECS
echo "[1/7] Scaling ECS service to 0 tasks..."
aws ecs update-service \
  --cluster $CLUSTER \
  --service $SERVICE \
  --desired-count 0 \
  --region $REGION \
  --query 'service.{Name:serviceName,DesiredCount:desiredCount,RunningCount:runningCount}' \
  --output table
echo "✓ ECS service scaled down"
echo ""

# 2. Delete RDS (no user data, skip snapshot)
echo "[2/7] Deleting RDS database (no snapshot - no user data)..."
aws rds delete-db-instance \
  --db-instance-identifier $DB_INSTANCE \
  --skip-final-snapshot \
  --delete-automated-backups \
  --region $REGION \
  --query '{DBInstanceIdentifier:DBInstanceIdentifier,Status:DBInstanceStatus}' \
  --output table || echo "RDS already deleted or not found"
echo "✓ RDS deletion initiated (will complete in 5-10 minutes)"
echo ""

# 3. Delete ElastiCache Redis
echo "[3/7] Deleting ElastiCache Redis..."
aws elasticache delete-replication-group \
  --replication-group-id $REDIS_GROUP \
  --region $REGION \
  --query '{ReplicationGroupId:ReplicationGroupId,Status:Status}' \
  --output table || echo "Redis already deleted or not found"
echo "✓ Redis deletion initiated (will complete in 5-10 minutes)"
echo ""

# 4. Get ALB ARN
echo "[4/7] Getting ALB details..."
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names $ALB_NAME \
  --region $REGION \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text 2>/dev/null) || echo "ALB not found"

if [ -n "$ALB_ARN" ] && [ "$ALB_ARN" != "None" ]; then
  echo "ALB ARN: $ALB_ARN"

  # 5. Delete ALB listeners first
  echo "[5/7] Deleting ALB listeners..."
  LISTENERS=$(aws elbv2 describe-listeners \
    --load-balancer-arn $ALB_ARN \
    --region $REGION \
    --query 'Listeners[*].ListenerArn' \
    --output text 2>/dev/null)

  if [ -n "$LISTENERS" ]; then
    for listener in $LISTENERS; do
      aws elbv2 delete-listener --listener-arn $listener --region $REGION
      echo "  ✓ Deleted listener: $listener"
    done
  fi
  echo "✓ All listeners deleted"
  echo ""

  # 6. Delete ALB
  echo "[6/7] Deleting Application Load Balancer..."
  aws elbv2 delete-load-balancer \
    --load-balancer-arn $ALB_ARN \
    --region $REGION
  echo "✓ ALB deletion initiated"
  echo ""

  # Wait for ALB deletion before deleting target group
  echo "Waiting 180 seconds for ALB deletion..."
  sleep 180

  # 7. Delete Target Group
  echo "[7/7] Deleting target group..."
  TG_ARN=$(aws elbv2 describe-target-groups \
    --names $TG_NAME \
    --region $REGION \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text 2>/dev/null) || echo "Target group not found"

  if [ -n "$TG_ARN" ] && [ "$TG_ARN" != "None" ]; then
    aws elbv2 delete-target-group \
      --target-group-arn $TG_ARN \
      --region $REGION
    echo "✓ Target group deleted"
  else
    echo "Target group already deleted or not found"
  fi
else
  echo "ALB not found, skipping ALB and target group deletion"
fi

echo ""
echo "======================================"
echo "Shutdown Complete!"
echo "======================================"
echo ""
echo "✓ ECS service scaled to 0"
echo "✓ RDS database deletion in progress"
echo "✓ ElastiCache Redis deletion in progress"
echo "✓ ALB deleted"
echo "✓ Target group deleted"
echo ""
echo "Still running (minimal cost):"
echo "  - CloudFront distribution (~$5/month)"
echo "  - S3 frontend bucket (~$0.02/month)"
echo "  - ECR Docker images (~$1/month)"
echo "  - Secrets Manager (~$1.60/month for 4 secrets)"
echo ""
echo "Total monthly cost after shutdown: ~$8/month"
echo "Monthly savings: ~$120-150/month"
echo ""
echo "To completely shut down frontend:"
echo "  1. Disable CloudFront: aws cloudfront get-distribution-config --id <CLOUDFRONT_DISTRIBUTION_ID>"
echo "  2. Empty S3 bucket: aws s3 rm s3://${S3_BUCKET}/ --recursive"
echo ""
echo "To restart: See docs/deployment/restart-guide.md"
echo ""
