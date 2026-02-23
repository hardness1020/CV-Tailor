# Deployment Pipeline

Complete guide for deploying CV Tailor frontend and backend to AWS production.

## Prerequisites

Before deploying, ensure you have:

- [ ] AWS CLI configured with appropriate credentials
- [ ] Docker installed and running
- [ ] Access to AWS account <AWS_ACCOUNT_ID>
- [ ] Required environment variables (see `.env.production`)
- [ ] Code changes committed and pushed to Git

## Quick Deployment

### Deploy Frontend

```bash
cd frontend
npm run build
aws s3 sync dist/ s3://<YOUR_S3_BUCKET>/ --delete --region <AWS_REGION>
aws cloudfront create-invalidation --distribution-id <CLOUDFRONT_DISTRIBUTION_ID> --paths "/*"
```

Or use the deployment script:
```bash
./scripts/deploy-frontend.sh
```

### Deploy Backend

```bash
# Build and push Docker image
docker buildx build --platform linux/amd64 -t cv-tailor-backend:latest -f backend/Dockerfile backend --load
docker tag cv-tailor-backend:latest <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/cv-tailor/production:latest
aws ecr get-login-password --region <AWS_REGION> | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com
docker push <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/cv-tailor/production:latest

# Force ECS to deploy new image
aws ecs update-service --cluster <YOUR_ECS_CLUSTER> --service <YOUR_ECS_SERVICE> --force-new-deployment --region <AWS_REGION>
```

Or use the deployment script:
```bash
./scripts/deploy-backend.sh
```

## Detailed Deployment Process

### Frontend Deployment

#### 1. Pre-Deployment Checks

```bash
# Verify environment configuration
cat frontend/.env.production

# Run tests (if applicable)
cd frontend
npm test

# Type check
npm run typecheck

# Lint
npm run lint
```

#### 2. Build Production Bundle

```bash
cd frontend
npm run build  # or: npx vite build
```

Expected output:
- Build artifacts in `dist/` directory
- Total size ~736 KB
- No TypeScript errors
- No build warnings (check for critical warnings)

#### 3. Upload to S3

```bash
aws s3 sync dist/ s3://<YOUR_S3_BUCKET>/ --delete --region <AWS_REGION>
```

The `--delete` flag removes files from S3 that are not in the local `dist/` directory.

#### 4. Invalidate CloudFront Cache

```bash
aws cloudfront create-invalidation \
  --distribution-id <CLOUDFRONT_DISTRIBUTION_ID> \
  --paths "/*"
```

This ensures users get the latest version immediately (not cached version).

#### 5. Verify Frontend Deployment

```bash
# Check CloudFront URL
curl -I https://<YOUR_CLOUDFRONT_DOMAIN>

# Visit in browser
open https://<YOUR_CLOUDFRONT_DOMAIN>
```

Expected:
- HTTP 200 OK
- Content-Type: text/html
- App loads correctly in browser
- No console errors

### Backend Deployment

#### 1. Pre-Deployment Checks

```bash
# Run tests
docker-compose exec backend uv run python manage.py test --keepdb

# Check for migrations
docker-compose exec backend uv run python manage.py makemigrations --check --dry-run
```

#### 2. Build Docker Image

**Important**: Always build for `linux/amd64` platform (AWS ECS requirement).

```bash
docker buildx build \
  --platform linux/amd64 \
  -t cv-tailor-backend:latest \
  -f backend/Dockerfile \
  backend \
  --load
```

Expected:
- Build completes successfully
- Final image size: ~294MB compressed
- No build errors

**Verify image locally** (important to catch issues before deployment):

```bash
# Test image starts correctly
docker run --rm -p 8001:8000 cv-tailor-backend:latest

# Check health endpoint
curl http://localhost:8001/health/

# Stop test container
docker stop $(docker ps -q --filter ancestor=cv-tailor-backend:latest)
```

#### 3. Tag and Push to ECR

```bash
# Tag image for ECR
docker tag cv-tailor-backend:latest \
  <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/cv-tailor/production:latest

# Login to ECR
aws ecr get-login-password --region <AWS_REGION> | \
  docker login --username AWS --password-stdin \
  <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com

# Push image
docker push <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/cv-tailor/production:latest
```

Expected:
- Push shows layers uploading
- Final digest printed (e.g., `sha256:3d583c6709df...`)
- No authentication errors

#### 4. Deploy to ECS

```bash
aws ecs update-service \
  --cluster <YOUR_ECS_CLUSTER> \
  --service <YOUR_ECS_SERVICE> \
  --force-new-deployment \
  --region <AWS_REGION>
```

This triggers a rolling deployment:
1. ECS pulls the new image from ECR
2. Starts new tasks with the new image
3. Waits for new tasks to pass health checks
4. Drains connections from old tasks
5. Stops old tasks

#### 5. Monitor Deployment

```bash
# Check service status
aws ecs describe-services \
  --cluster <YOUR_ECS_CLUSTER> \
  --services <YOUR_ECS_SERVICE> \
  --region <AWS_REGION> \
  --query 'services[0].{RunningCount:runningCount,DesiredCount:desiredCount,Events:events[0:5]}'

# Watch task status (repeat every 30 seconds)
watch -n 30 'aws ecs list-tasks \
  --cluster <YOUR_ECS_CLUSTER> \
  --service-name <YOUR_ECS_SERVICE> \
  --region <AWS_REGION> | head -20'

# View logs (for debugging)
aws logs tail <YOUR_LOG_GROUP> --since 5m --region <AWS_REGION> --follow
```

**What to look for**:
- Running count matches desired count (2/2)
- New tasks show "RUNNING" status
- Health checks passing (HEALTHY status)
- No deployment errors in events

**Expected timeline**:
- 0-60s: New tasks start and pull image
- 60-180s: Django initializes, health check grace period
- 180-240s: Health checks pass, old tasks drain
- 240-300s: Old tasks stopped, deployment complete

#### 6. Verify Backend Deployment

```bash
# Check health endpoint
curl http://<YOUR_ALB_DNS>/health/

# Check API endpoint
curl http://<YOUR_ALB_DNS>/api/
```

Expected responses:
- Health: `{"status": "healthy"}` or similar
- API: JSON response (not 502 Bad Gateway)

## Post-Deployment Verification

### End-to-End Test

1. Visit frontend: https://<YOUR_CLOUDFRONT_DOMAIN>
2. Verify app loads without errors
3. Check browser console for errors
4. Test key user flows:
   - User registration/login
   - Artifact upload
   - CV generation
   - Document export

### Monitoring

```bash
# Check ECS service events
aws ecs describe-services \
  --cluster <YOUR_ECS_CLUSTER> \
  --services <YOUR_ECS_SERVICE> \
  --region <AWS_REGION> \
  --query 'services[0].events[0:10]'

# Check CloudWatch logs
aws logs tail <YOUR_LOG_GROUP> --since 10m --region <AWS_REGION>

# Check ALB target health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names <YOUR_TARGET_GROUP> \
    --region <AWS_REGION> \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text) \
  --region <AWS_REGION>
```

## Rollback Procedure

If deployment fails or introduces critical bugs:

### Frontend Rollback

```bash
# List previous S3 versions (if versioning enabled)
aws s3api list-object-versions \
  --bucket <YOUR_S3_BUCKET> \
  --prefix index.html

# Or re-deploy previous Git commit
git checkout <previous-commit>
cd frontend
npm run build
aws s3 sync dist/ s3://<YOUR_S3_BUCKET>/ --delete --region <AWS_REGION>
aws cloudfront create-invalidation --distribution-id <CLOUDFRONT_DISTRIBUTION_ID> --paths "/*"
```

### Backend Rollback

```bash
# List previous task definitions
aws ecs list-task-definitions \
  --family-prefix <YOUR_ECS_TASK_DEFINITION> \
  --region <AWS_REGION>

# Update service to use previous task definition
aws ecs update-service \
  --cluster <YOUR_ECS_CLUSTER> \
  --service <YOUR_ECS_SERVICE> \
  --task-definition <YOUR_ECS_TASK_DEFINITION>:<previous-revision> \
  --region <AWS_REGION>

# Or re-deploy previous Docker image
docker pull <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/cv-tailor/production:<previous-tag>
docker tag <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/cv-tailor/production:<previous-tag> \
  <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/cv-tailor/production:latest
docker push <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/cv-tailor/production:latest
aws ecs update-service --cluster <YOUR_ECS_CLUSTER> \
  --service <YOUR_ECS_SERVICE> --force-new-deployment --region <AWS_REGION>
```

## Common Issues

See [Troubleshooting](./troubleshooting.md) for detailed solutions to common deployment issues.

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing locally
- [ ] Database migrations created (if needed)
- [ ] Environment variables updated (if needed)
- [ ] Code reviewed and approved
- [ ] Git commit created with descriptive message

### Frontend Deployment
- [ ] Build completes without errors
- [ ] S3 sync successful
- [ ] CloudFront invalidation created
- [ ] Frontend accessible via HTTPS

### Backend Deployment
- [ ] Docker build completes (294MB)
- [ ] Image tested locally
- [ ] ECR push successful
- [ ] ECS deployment initiated
- [ ] New tasks healthy (2/2)
- [ ] Health endpoint responding
- [ ] API endpoints responding

### Post-Deployment
- [ ] End-to-end tests passing
- [ ] No errors in CloudWatch logs
- [ ] ALB targets healthy
- [ ] User flows working as expected
- [ ] Deployment documented

## Support

- **Current Status**: [current-deployment.md](./current-deployment.md)
- **Architecture**: [architecture.md](./architecture.md)
- **Troubleshooting**: [troubleshooting.md](./troubleshooting.md)
