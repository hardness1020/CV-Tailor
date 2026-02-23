#!/bin/bash
set -e

# CV-Tailor Backend Deployment Script
# Builds and deploys Django backend to AWS ECS

# Load shared configuration
SCRIPT_DIR="$(dirname "$0")"
source "${SCRIPT_DIR}/config.sh"

echo "============================================"
echo "CV-Tailor Backend Deployment"
echo "============================================"
echo ""

# Image tag (default: latest, or pass as first argument)
IMAGE_TAG="${1:-latest}"

# Derived values
IMAGE_FULL="${ECR_URI}:${IMAGE_TAG}"

echo "Configuration:"
echo "  Region: ${AWS_REGION}"
echo "  Account: ${AWS_ACCOUNT_ID}"
echo "  ECR Repository: ${ECR_REPOSITORY}"
echo "  Image Tag: ${IMAGE_TAG}"
echo "  Cluster: ${CLUSTER_NAME}"
echo "  Service: ${SERVICE_NAME}"
echo ""

# Step 1: Login to ECR
echo "Step 1/5: Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin ${ECR_URI}
echo "✅ ECR login successful"
echo ""

# Step 2: Build Docker image
echo "Step 2/5: Building Docker image for linux/amd64..."
echo "  Building from: backend/Dockerfile"
cd backend
docker buildx build --platform linux/amd64 -t cv-tailor-backend:${IMAGE_TAG} -f Dockerfile . --load
echo "✅ Docker image built successfully"
echo ""

# Step 3: Tag image for ECR
echo "Step 3/5: Tagging image for ECR..."
docker tag cv-tailor-backend:${IMAGE_TAG} ${IMAGE_FULL}
echo "  Tagged as: ${IMAGE_FULL}"
echo "✅ Image tagged"
echo ""

# Step 4: Push to ECR
echo "Step 4/5: Pushing image to ECR..."
echo "  This may take a few minutes..."
docker push ${IMAGE_FULL}
echo "✅ Image pushed to ECR"
echo ""

# Step 5: Update ECS service
echo "Step 5/5: Updating ECS service..."
cd ..
aws ecs update-service \
  --cluster ${CLUSTER_NAME} \
  --service ${SERVICE_NAME} \
  --force-new-deployment \
  --region ${AWS_REGION} \
  --output json > /dev/null

echo "✅ ECS service update initiated"
echo ""

# Wait for deployment to stabilize
echo "Waiting for deployment to stabilize..."
echo "  This may take 5-10 minutes..."
echo "  You can check progress with: ./scripts/check-health.sh"
echo ""

aws ecs wait services-stable \
  --cluster ${CLUSTER_NAME} \
  --services ${SERVICE_NAME} \
  --region ${AWS_REGION}

echo "✅ Deployment complete!"
echo ""

# Check task status
echo "Current task status:"
TASKS=$(aws ecs list-tasks \
  --cluster ${CLUSTER_NAME} \
  --service-name ${SERVICE_NAME} \
  --region ${AWS_REGION} \
  --query 'taskArns' \
  --output text)

if [ -z "$TASKS" ]; then
  echo "  ⚠️  No tasks running yet. Check logs with: ./scripts/view-logs.sh"
else
  TASK_COUNT=$(echo $TASKS | wc -w)
  echo "  ✅ ${TASK_COUNT} task(s) running"
fi
echo ""

# Prompt for migrations
echo "============================================"
echo "Next Steps"
echo "============================================"
echo ""
echo "1. Run database migrations:"
echo "   ./scripts/run-migrations.sh"
echo ""
echo "2. Check application health:"
echo "   ./scripts/check-health.sh"
echo ""
echo "3. View application logs:"
echo "   ./scripts/view-logs.sh"
echo ""

read -p "Would you like to run migrations now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo ""
  ./scripts/run-migrations.sh
fi

echo ""
echo "🎉 Backend deployment complete!"
echo ""
