# CV Tailor Production Scripts

This directory contains automation scripts for deploying, managing, and monitoring the CV Tailor production infrastructure on AWS.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Script Reference](#script-reference)
- [Common Workflows](#common-workflows)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before using these scripts, ensure you have:

### Required Tools

- **AWS CLI** (v2.x or later) - [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- **Docker** (with buildx support) - [Installation Guide](https://docs.docker.com/get-docker/)
- **Node.js** (v18+) and npm - Required for frontend deployment
- **jq** - JSON processor for parsing AWS CLI output
  ```bash
  # macOS
  brew install jq

  # Ubuntu/Debian
  sudo apt-get install jq
  ```

### AWS Configuration

1. **Configure AWS CLI credentials:**
   ```bash
   aws configure
   ```
   - Region: `<AWS_REGION>`
   - Account ID: `<AWS_ACCOUNT_ID>`

2. **Verify access:**
   ```bash
   aws sts get-caller-identity
   ```

### Permissions Required

Your AWS user/role needs permissions for:
- ECS (tasks, services, clusters)
- ECR (push/pull images)
- RDS (describe, start, stop, modify, delete instances)
- ElastiCache (describe, delete replication groups)
- ELBv2 (load balancers, target groups, listeners)
- S3 (read/write to frontend bucket)
- CloudFront (create invalidations)
- CloudWatch Logs (read log streams)
- Secrets Manager (optional, for production secrets)

## Configuration

All scripts source shared configuration from `config.sh`. To customize for your environment:

### Edit config.sh

```bash
vim scripts/config.sh
```

**Key Configuration Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `<AWS_REGION>` | AWS region for all resources |
| `AWS_ACCOUNT_ID` | `<AWS_ACCOUNT_ID>` | AWS account ID |
| `FRONTEND_URL` | `https://<YOUR_DOMAIN>` | Production frontend URL |
| `API_URL` | `https://api.<YOUR_DOMAIN>` | Production API URL |
| `CLUSTER_NAME` | `<YOUR_ECS_CLUSTER>` | ECS cluster name |
| `SERVICE_NAME` | `<YOUR_ECS_SERVICE>` | ECS service name |
| `S3_BUCKET` | `<YOUR_S3_BUCKET>` | Frontend S3 bucket |
| `CLOUDFRONT_ID` | `<YOUR_CLOUDFRONT_ID>` | CloudFront distribution ID |

**Note:** After editing `config.sh`, all scripts will automatically use the updated values.

## Script Reference

### Setup & Initial Deployment

#### `aws-setup.sh`
**Purpose:** One-time AWS infrastructure setup
**Creates:**
- S3 bucket for Terraform state
- DynamoDB table for state locking
- GitHub Actions OIDC provider
- IAM role for GitHub Actions

**Usage:**
```bash
./scripts/aws-setup.sh
```

**When to use:** First-time setup or when recreating CI/CD infrastructure

---

### Deployment Scripts

#### `deploy-backend.sh [IMAGE_TAG]`
**Purpose:** Build and deploy Django backend to ECS
**Steps:**
1. Login to ECR
2. Build Docker image for linux/amd64
3. Tag and push to ECR
4. Force new ECS deployment
5. Wait for service to stabilize

**Usage:**
```bash
# Deploy with latest tag (default)
./scripts/deploy-backend.sh

# Deploy with specific tag
./scripts/deploy-backend.sh v1.2.3
```

**Duration:** ~5-10 minutes

**Next steps:** The script will prompt you to run migrations

---

#### `deploy-frontend.sh`
**Purpose:** Build and deploy React frontend to S3/CloudFront
**Steps:**
1. Install npm dependencies (if needed)
2. Build production bundle with `VITE_API_BASE_URL`
3. Upload to S3 with cache optimization
4. Invalidate CloudFront cache

**Usage:**
```bash
./scripts/deploy-frontend.sh
```

**Duration:** ~3-5 minutes

**Note:** Frontend automatically configured to use `API_URL` from config.sh

---

#### `run-migrations.sh`
**Purpose:** Run Django database migrations via ECS Exec
**Requirements:**
- At least one running ECS task
- ECS Exec enabled on task definition

**Usage:**
```bash
./scripts/run-migrations.sh
```

**Interactive:** Optionally prompts to create Django superuser

---

### Monitoring & Health Checks

#### `check-health.sh`
**Purpose:** Comprehensive health check of all production services
**Checks:**
1. ECS service status (desired vs running tasks)
2. Individual task health
3. ALB target group health
4. Backend API `/health/` endpoint
5. Frontend availability

**Usage:**
```bash
./scripts/check-health.sh
```

**Output:** Detailed status with ✅/❌/⚠️ indicators

---

#### `view-logs.sh`
**Purpose:** Interactive CloudWatch log viewer
**Options:**
1. Tail logs (follow mode)
2. Last 100 lines
3. Last 1 hour
4. Search for errors

**Usage:**
```bash
./scripts/view-logs.sh
# Then select option 1-4
```

**Tip:** Use option 4 to quickly find errors

---

### Cost Management

#### `shutdown-production.sh`
**Purpose:** Graceful shutdown of production to minimize costs
**Shuts down:**
- ECS service (scales to 0)
- RDS database (deletes, no snapshot)
- ElastiCache Redis (deletes)
- Application Load Balancer
- Target Group

**Keeps running:**
- CloudFront distribution
- S3 frontend bucket
- ECR Docker images
- Secrets Manager secrets

**Usage:**
```bash
./scripts/shutdown-production.sh
```

**Confirmation:** Requires typing `yes` to proceed

**Savings:** ~$120/month (reduces cost from ~$128/month to ~$8/month)

**Warning:** This deletes the RDS database without a snapshot (acceptable since no user data exists). For production with real data, modify the script to keep a snapshot.

---

#### `restart-production.sh`
**Purpose:** Restart production infrastructure after shutdown
**Restart modes:**

1. **Quick Restart** (if infrastructure exists but stopped):
   - Start RDS database
   - Scale ECS service to 2 tasks
   - Duration: ~5-10 minutes

2. **Full Restart** (if infrastructure deleted):
   - Guides you to manual recreation steps
   - See `docs/deployment/restart-guide.md`
   - Duration: ~30-60 minutes

**Usage:**
```bash
./scripts/restart-production.sh
```

**Health Check:** Automatically verifies backend API after restart

---

## Common Workflows

### Initial Setup (First-Time)

```bash
# 1. Setup AWS prerequisites
./scripts/aws-setup.sh

# 2. Deploy backend
./scripts/deploy-backend.sh

# 3. Run migrations
./scripts/run-migrations.sh

# 4. Deploy frontend
./scripts/deploy-frontend.sh

# 5. Verify deployment
./scripts/check-health.sh
```

---

### Regular Backend Deployment

```bash
# 1. Deploy new backend version
./scripts/deploy-backend.sh

# 2. Run migrations (if needed)
./scripts/run-migrations.sh

# 3. Check health
./scripts/check-health.sh

# 4. Monitor logs if needed
./scripts/view-logs.sh
```

---

### Regular Frontend Deployment

```bash
# 1. Deploy frontend
./scripts/deploy-frontend.sh

# 2. Verify frontend
open https://<YOUR_DOMAIN>
```

---

### Debugging Production Issues

```bash
# 1. Check overall health
./scripts/check-health.sh

# 2. View recent logs
./scripts/view-logs.sh
# Select option 2 or 3

# 3. Search for errors
./scripts/view-logs.sh
# Select option 4

# 4. Check specific AWS resource
aws ecs describe-services --cluster <YOUR_ECS_CLUSTER> --service <YOUR_ECS_SERVICE> --region <AWS_REGION>
```

---

### Cost Optimization (Shutdown/Restart)

**Shutdown for extended period:**
```bash
# Shutdown infrastructure
./scripts/shutdown-production.sh

# Later, restart when needed
./scripts/restart-production.sh
```

**Monthly Cost Breakdown:**

| State | Monthly Cost | Details |
|-------|-------------|---------|
| **Running** | ~$128/month | ECS ($30-40) + RDS ($25-30) + Redis ($15-20) + ALB ($20) + Other ($8) |
| **Shutdown** | ~$8/month | CloudFront ($5) + S3 ($0.02) + ECR ($1) + Secrets ($1.60) |
| **Savings** | ~$120/month | 93% cost reduction |

---

## Troubleshooting

### Common Issues

#### "No tasks running" after deployment

**Cause:** Task may be failing to start

**Solution:**
```bash
# Check service events
aws ecs describe-services --cluster <YOUR_ECS_CLUSTER> --service <YOUR_ECS_SERVICE> --region <AWS_REGION>

# Check logs for errors
./scripts/view-logs.sh
# Select option 4 (search for errors)
```

---

#### "Backend API not responding"

**Cause:** Tasks may not be healthy or ALB target group unhealthy

**Solution:**
```bash
# Check target health
./scripts/check-health.sh

# Verify tasks are running
aws ecs list-tasks --cluster <YOUR_ECS_CLUSTER> --service <YOUR_ECS_SERVICE> --region <AWS_REGION>

# Check ALB target group
aws elbv2 describe-target-health --target-group-arn <ARN> --region <AWS_REGION>
```

---

#### "Permission denied" when running scripts

**Cause:** Scripts not executable

**Solution:**
```bash
chmod +x scripts/*.sh
```

---

#### "AWS CLI not configured"

**Cause:** AWS credentials not set

**Solution:**
```bash
aws configure
# Enter access key, secret key, region
```

---

#### "Docker buildx not available"

**Cause:** Docker buildx not installed or enabled

**Solution:**
```bash
# macOS/Linux - Install buildx
docker buildx install

# Verify
docker buildx version
```

---

#### "CloudFront invalidation taking too long"

**Cause:** CloudFront invalidations can take 5-15 minutes

**Solution:**
- Script waits for completion automatically
- You can continue work while invalidation completes
- Check status manually:
  ```bash
  aws cloudfront get-invalidation --distribution-id <YOUR_CLOUDFRONT_ID> --id <INVALIDATION_ID> --region <AWS_REGION>
  ```

---

#### "RDS deletion protection" during shutdown

**Cause:** RDS instance has deletion protection enabled

**Solution:**
- Script automatically disables deletion protection
- If manual intervention needed:
  ```bash
  aws rds modify-db-instance --db-instance-identifier <YOUR_RDS_INSTANCE> --no-deletion-protection --apply-immediately --region <AWS_REGION>
  ```

---

## Additional Resources

- **Deployment Documentation:** `docs/deployment/`
- **Architecture Diagrams:** `docs/deployment/architecture.md`
- **Deployment Pipeline:** `docs/deployment/deployment-pipeline.md`

---

## Script Maintenance

### Adding a New Script

1. Create the script in `scripts/`
2. Add configuration loading:
   ```bash
   #!/bin/bash
   SCRIPT_DIR="$(dirname "$0")"
   source "${SCRIPT_DIR}/config.sh"
   ```
3. Use config variables instead of hardcoded values
4. Update this README with script documentation

### Modifying Configuration

1. Edit `scripts/config.sh`
2. Update this README if adding new variables
3. Test all scripts to ensure compatibility

---

**Last Updated:** 2025-10-24
**Maintained by:** CV Tailor Development Team
