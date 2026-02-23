# CV-Tailor Terraform Infrastructure

> **⚠️ IMPORTANT: This Terraform configuration is NOT currently deployed to production.**
>
> **For actual production deployment documentation**, see **[docs/deployment/](../docs/deployment/)** directory.
>
> The actual production deployment (October 23, 2025) was done manually via AWS Console and CLI.
> This Terraform code represents infrastructure-as-code for future automated deployments.
>
> **Key Differences from Production**:
> - CloudFront Distribution ID: Terraform would create new (E25GXY9876W11S) vs actual (<CLOUDFRONT_DISTRIBUTION_ID>)
> - Resource naming may differ from manually created resources
> - Configuration parameters may not match exact production setup
>
> **To see what's actually running in production**, refer to:
> - [Current Deployment Status](../docs/deployment/current-deployment.md)
> - [Deployment Pipeline](../docs/deployment/deployment-pipeline.md)
> - [Architecture Diagram](../docs/deployment/architecture.md)

---

Production-ready AWS infrastructure for CV-Tailor application using Terraform (for future deployments).

## Architecture Overview (Cost-Optimized B1 Configuration)

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Route 53   │  (DNS - Manual)
                    └──────┬──────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      VPC (10.0.0.0/16)                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Public Subnets (2 AZs)                 │   │
│  │  ┌────────────────────────────────────────────┐    │   │
│  │  │  Application Load Balancer (ALB)           │    │   │
│  │  │  - HTTPS (443) → ECS Tasks                 │    │   │
│  │  │  - HTTP (80) → Redirect to HTTPS           │    │   │
│  │  └────────────────────────────────────────────┘    │   │
│  │  ┌────────────────────────────────────────────┐    │   │
│  │  │  ECS Fargate Tasks (2 tasks)               │    │   │
│  │  │  - Django Backend (Port 8000)              │    │   │
│  │  │  - 1 vCPU, 2GB RAM per task                │    │   │
│  │  │  - Public IPs (ALB-protected)              │    │   │
│  │  └────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│  ┌────────────────────────▼────────────────────────────┐   │
│  │              Private Subnets (2 AZs)                │   │
│  │  ┌────────────────────────────────────────────┐    │   │
│  │  │  RDS PostgreSQL 15 (Single-AZ)             │    │   │
│  │  │  - db.t4g.small (2 vCPU, 2GB RAM)          │    │   │
│  │  │  - 50 GB SSD with auto-scaling             │    │   │
│  │  └────────────────────────────────────────────┘    │   │
│  │  ┌────────────────────────────────────────────┐    │   │
│  │  │  ElastiCache Redis 7.0                     │    │   │
│  │  │  - cache.t4g.micro (1 node)                │    │   │
│  │  └────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘

Note: NAT Gateway REMOVED for cost savings ($35-40/month)
      ECS tasks use public subnets with direct internet access

┌───────────────────────────────────────────────────────────────┐
│                     External Services                         │
│  ┌────────────────────────────────────────────┐              │
│  │  CloudFront CDN (Frontend)                 │              │
│  │  - Global edge locations                   │              │
│  │  - S3 origin (React SPA)                   │              │
│  │  - HTTPS with custom domain support        │              │
│  └────────────────────────────────────────────┘              │
│  ┌────────────────────────────────────────────┐              │
│  │  S3 Buckets                                │              │
│  │  - Frontend bucket (React app)             │              │
│  │  - Media bucket (user uploads)             │              │
│  │  - Static bucket (Django static files)     │              │
│  └────────────────────────────────────────────┘              │
│  ┌────────────────────────────────────────────┐              │
│  │  ECR (Docker Registry)                     │              │
│  └────────────────────────────────────────────┘              │
│  ┌────────────────────────────────────────────┐              │
│  │  CloudWatch (Monitoring & Logs)            │              │
│  │  - Dashboard                                │              │
│  │  - Alarms → SNS → Email                    │              │
│  └────────────────────────────────────────────┘              │
│  ┌────────────────────────────────────────────┐              │
│  │  Secrets Manager                            │              │
│  │  - Database credentials                     │              │
│  │  - Redis auth token                         │              │
│  │  - Django SECRET_KEY                        │              │
│  └────────────────────────────────────────────┘              │
└───────────────────────────────────────────────────────────────┘
```

## Infrastructure Components

### Networking (VPC Module)
- **VPC**: 10.0.0.0/16 CIDR block
- **Public Subnets**: 2 subnets across 2 AZs (for ALB)
- **Private Subnets**: 2 subnets across 2 AZs (for ECS, RDS, Redis)
- **NAT Gateway**: 1 gateway for cost optimization (all private subnets route through it)
- **Internet Gateway**: Public internet access

### Security (Security Module)
- **IAM Roles**:
  - ECS Execution Role: Pull images, write logs, read secrets
  - ECS Task Role: Access S3, Secrets Manager
- **Security Groups**:
  - ALB SG: Allow 80/443 from internet
  - ECS Tasks SG: Allow 8000 from ALB
  - RDS SG: Allow 5432 from ECS tasks
  - ElastiCache SG: Allow 6379 from ECS tasks

### Database (RDS Module)
- **Engine**: PostgreSQL 15.4
- **Instance**: db.t4g.small (2 vCPU, 2 GB RAM)
- **Storage**: 100 GB SSD with auto-scaling
- **Multi-AZ**: Enabled for high availability
- **Backups**: 30-day retention
- **Encryption**: At rest and in transit

### Cache (ElastiCache Module)
- **Engine**: Redis 7.0
- **Instance**: cache.t4g.small (1 node)
- **Encryption**: At rest and in transit
- **AUTH**: Enabled (password stored in Secrets Manager)

### Storage (S3 Module)
- **Media Bucket**: User uploads, generated documents
- **Static Bucket**: Django static files (CSS, JS, images)
- **Frontend Bucket**: React SPA static files (private, CloudFront access only)
- **Versioning**: Enabled on all buckets
- **Lifecycle Policies**: Archive old files to Glacier

### CloudFront (Frontend CDN Module)
- **Distribution**: Global CDN for React frontend
- **Origin**: S3 bucket (frontend) with Origin Access Identity
- **Price Class**: PriceClass_100 (US, Canada, Europe)
- **Cache Behaviors**:
  - Default: index.html and SPA routes (1 hour TTL)
  - Assets (/assets/*): Long-term caching (1 year TTL)
- **Custom Errors**: 404/403 → index.html (for SPA routing)
- **HTTPS**: SSL/TLS with optional custom domain
- **Compression**: Automatic gzip/brotli
- **Cost**: ~$1-3/month for low traffic

### Load Balancer (ALB Module)
- **Type**: Application Load Balancer
- **Listeners**:
  - HTTPS (443): SSL/TLS termination → ECS tasks
  - HTTP (80): Redirect to HTTPS
- **Health Checks**: /health/ endpoint
- **Target Group**: IP-based for Fargate

### Container Orchestration (ECS Module)
- **Cluster**: ECS Fargate
- **Tasks**: 2 vCPU, 4 GB RAM each
- **Desired Count**: 2 tasks for HA
- **Auto-scaling**: Disabled (manual scaling)
- **Container Port**: 8000
- **Logs**: CloudWatch with 7-day retention

### Monitoring (Monitoring Module)
- **Dashboard**: Centralized CloudWatch dashboard
- **Metrics**: ALB, ECS, RDS, ElastiCache
- **Alarms**: CPU, memory, health, errors
- **Notifications**: SNS → Email

## Prerequisites

Before deploying, ensure you have:

1. **AWS Account** with appropriate permissions
2. **Terraform** >= 1.5.0 installed
3. **AWS CLI** configured with credentials
4. **S3 Bucket** for Terraform state (see below)
5. **DynamoDB Table** for state locking (see below)
6. **ACM Certificate** for HTTPS (optional but recommended)

### Create State Backend Resources

```bash
# Create S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket <YOUR_STATE_BUCKET> \
  --region <AWS_REGION> \
  --create-bucket-configuration LocationConstraint=<AWS_REGION>

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket <YOUR_STATE_BUCKET> \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket <YOUR_STATE_BUCKET> \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name <YOUR_LOCK_TABLE> \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region <AWS_REGION>
```

### Create ACM Certificate (Optional)

```bash
# Request certificate for your domain
aws acm request-certificate \
  --domain-name api.<YOUR_DOMAIN> \
  --validation-method DNS \
  --region <AWS_REGION>

# Follow DNS validation steps in AWS Console
# Copy the certificate ARN to production.tfvars
```

## Deployment

### 1. Configure Variables

Edit `environments/production.tfvars`:

```hcl
# Required: Add your certificate ARN
certificate_arn = "arn:aws:acm:<AWS_REGION>:<AWS_ACCOUNT_ID>:certificate/<CERTIFICATE_ID>"

# Required: Add your alarm email
alarm_email = "<YOUR_EMAIL>"

# Optional: Customize other settings
desired_count = 2
rds_multi_az = true
```

### 2. Initialize Terraform

```bash
cd terraform

terraform init \
  -backend-config="bucket=<YOUR_STATE_BUCKET>" \
  -backend-config="key=production/terraform.tfstate" \
  -backend-config="region=<AWS_REGION>" \
  -backend-config="encrypt=true" \
  -backend-config="dynamodb_table=<YOUR_LOCK_TABLE>"
```

### 3. Validate Configuration

```bash
terraform validate
terraform fmt -check -recursive
```

### 4. Plan Deployment

```bash
terraform plan -var-file=environments/production.tfvars -out=tfplan
```

Review the plan carefully before applying.

### 5. Apply Configuration

```bash
terraform apply tfplan
```

This will create ~40+ AWS resources. Deployment takes approximately 15-20 minutes.

### 6. Verify Deployment

```bash
# Get outputs
terraform output

# Key outputs:
# - alb_dns_name: Load balancer DNS
# - ecr_repository_url: Docker registry URL
# - dashboard_url: CloudWatch dashboard URL
```

## Post-Deployment Steps

### 1. Confirm SNS Subscription

Check your email for SNS subscription confirmation and click the link.

### 2. Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region <AWS_REGION> | docker login --username AWS --password-stdin $(terraform output -raw ecr_repository_url | cut -d'/' -f1)

# Build image
docker build -t cv-tailor:latest ../backend/

# Tag image
docker tag cv-tailor:latest $(terraform output -raw ecr_repository_url):latest

# Push image
docker push $(terraform output -raw ecr_repository_url):latest
```

### 3. Update ECS Service

```bash
# Force new deployment with latest image
aws ecs update-service \
  --cluster <YOUR_ECS_CLUSTER> \
  --service <YOUR_ECS_SERVICE> \
  --force-new-deployment \
  --region <AWS_REGION>
```

### 4. Run Database Migrations

```bash
# Get ECS task ARN
TASK_ARN=$(aws ecs list-tasks --cluster <YOUR_ECS_CLUSTER> --service <YOUR_ECS_SERVICE> --region <AWS_REGION> --query 'taskArns[0]' --output text)

# Run migrations
aws ecs execute-command \
  --cluster <YOUR_ECS_CLUSTER> \
  --task $TASK_ARN \
  --container app \
  --command "python manage.py migrate" \
  --interactive \
  --region <AWS_REGION>
```

### 5. Create Django Superuser

```bash
aws ecs execute-command \
  --cluster <YOUR_ECS_CLUSTER> \
  --task $TASK_ARN \
  --container app \
  --command "python manage.py createsuperuser" \
  --interactive \
  --region <AWS_REGION>
```

### 6. Configure DNS

Point your domain to the ALB:

```bash
# Get ALB DNS name
terraform output alb_dns_name

# Create CNAME record in Route 53 or your DNS provider:
# api.<YOUR_DOMAIN> → <YOUR_ALB_DNS>
```

### 7. Collect Static Files

```bash
aws ecs execute-command \
  --cluster <YOUR_ECS_CLUSTER> \
  --task $TASK_ARN \
  --container app \
  --command "python manage.py collectstatic --noinput" \
  --interactive \
  --region <AWS_REGION>
```

## Cost Estimation

**This infrastructure uses a FREE TIER OPTIMIZED configuration** for AWS Free Tier eligible accounts (first 12 months).

Expected monthly costs with FREE TIER configuration:

| Service | Configuration | Monthly Cost (Free Tier) | After 12 Months |
|---------|---------------|--------------------------|-----------------|
| ECS Fargate | 2 tasks (1 vCPU, 2GB each) | $18-22 | $18-22 |
| RDS | db.t4g.micro, Single-AZ, 20GB | **$0** (750hrs free) | $12-15 |
| ElastiCache | cache.t4g.micro, 1 node | $10-13 | $10-13 |
| ALB | Application Load Balancer | $20-25 | $20-25 |
| ~~NAT Gateway~~ | **REMOVED** | ~~$35-40~~ **$0** | **$0** |
| S3 | Media + Static + Frontend | **$0** (< 5GB) | $3-6 |
| CloudFront | Frontend CDN (PriceClass_100) | **$0** (< 50GB) | $1-3 |
| CloudWatch | Logs + Metrics + Alarms | **$0** (< 10 alarms) | $3-5 |
| Secrets Manager | Application secrets | $1.50 | $1.50 |
| **TOTAL** | | **~$48-60/month** | **~$68-85/month** |

**💰 FREE TIER SAVINGS: ~$20-30/month for first 12 months**
**💰 Total savings vs full HA: ~$90-145/month (55-65% reduction)**

### What's Different in Free Tier Configuration?

**Cost Optimizations Applied:**
- ✅ **FREE TIER RDS**: db.t4g.micro (1 GB RAM) instead of db.t4g.small (saves $20-25/month for 12 months)
- ✅ **Reduced RDS storage**: 20GB instead of 50GB (free tier eligible)
- ✅ **NAT Gateway removed**: ECS tasks use public subnets (saves $35-40/month)
- ✅ **Single-AZ RDS**: No Multi-AZ replication (saves ~$20/month)
- ✅ **Reduced compute**: 1 vCPU per task instead of 2 (saves ~$17/month)
- ✅ **Smaller Redis**: cache.t4g.micro instead of small (saves ~$10/month)
- ✅ **Free tier S3/CloudFront**: Under limits for first 12 months (saves ~$4-9/month)

**What's Retained:**
- ✅ **Application HA**: Still 2 ECS tasks (zero downtime deployments)
- ✅ **HTTPS via ALB**: Full SSL/TLS termination
- ✅ **Full monitoring**: CloudWatch dashboard and alarms
- ✅ **Security**: Private RDS/Redis, ALB protects ECS tasks
- ✅ **Automated backups**: 7 days retention included in free tier

**Trade-offs:**
- ⚠️ **Reduced DB memory**: 1 GB RAM (adequate for dev/staging, may need upgrade for production)
- ⚠️ **Limited storage**: 20 GB database storage (can upgrade when needed)
- ⚠️ **Single-AZ database**: ~30 second downtime on RDS failure (rare)
- ⚠️ **Public subnet ECS**: Tasks have public IPs but protected by security groups
- ⚠️ **Time-limited**: Free tier expires after 12 months

### Upgrade Path (If Needed)

**Step 1: Upgrade from Free Tier to Paid Tier (after 12 months or for better performance)**

Update `production.tfvars`:
```hcl
# Upgrade RDS for better performance (adds $8-10/month)
rds_instance_class = "db.t4g.small"   # 2 GB RAM
rds_allocated_storage = 50             # More storage
rds_backup_retention_days = 14         # Longer retention
```

**Step 2: Enable Full HA Configuration (production-grade)**

Update `production.tfvars`:
```hcl
# Enable NAT Gateway (adds $35-40/month)
enable_nat_gateway = true
nat_gateway_count  = 1

# Enable Multi-AZ RDS (adds ~$20/month)
rds_multi_az = true
rds_allocated_storage = 100

# Increase compute resources (adds ~$17/month)
ecs_cpu = "2048"    # 2 vCPU
ecs_memory = "4096"  # 4 GB

# Upgrade Redis (adds ~$10/month)
redis_node_type = "cache.t4g.small"
```

Then update `main.tf`:
```hcl
# Line 198: Change ECS to use private subnets
private_subnet_ids = module.vpc.private_subnet_ids
```

And in `modules/ecs/main.tf`:
```hcl
# Line 216: Disable public IPs
assign_public_ip = false
```

**Total cost after upgrade: ~$160-205/month**

### Security Notes for B1 Configuration

**ECS Tasks in Public Subnets - Still Secure:**

1. **Not directly accessible**: Security groups block all inbound traffic except from ALB
2. **ALB is the only entry point**: Port 8000 only accepts connections from ALB SG
3. **RDS/Redis remain private**: Database and cache have no public IPs
4. **No NAT attack surface**: No NAT Gateway to compromise

Security group configuration:
```
ECS Tasks SG:
  Inbound:  Port 8000 from ALB SG ONLY
  Outbound: All (for Docker pulls, S3, internet access)

ALB SG:
  Inbound:  Port 80/443 from internet
  Outbound: Port 8000 to ECS tasks only
```

## Monitoring

### CloudWatch Dashboard

Access the dashboard:
```bash
terraform output dashboard_url
```

Key metrics:
- ALB: Request count, response time, HTTP codes, target health
- ECS: CPU/memory utilization, task count
- RDS: CPU, connections, storage, I/O latency
- ElastiCache: CPU, memory, cache hit/miss, evictions

### CloudWatch Alarms

Configured alarms:
- **ECS**: High CPU (>80%), high memory (>80%), no running tasks
- **RDS**: High CPU (>80%), low storage (<10GB), high connections (>80)
- **ElastiCache**: High CPU (>75%), high memory (>80%), evictions (>1000)
- **ALB**: High response time (>1s), 5xx errors (>10), unhealthy targets
- **Application**: Error logs (>10 in 5 min)

All alarms send notifications to SNS topic → email.

### Viewing Logs

```bash
# ECS application logs
aws logs tail /ecs/<YOUR_ECS_LOG_GROUP> --follow --region <AWS_REGION>

# RDS logs (slow queries)
aws rds describe-db-log-files --db-instance-identifier <YOUR_RDS_INSTANCE> --region <AWS_REGION>
```

## Updating Infrastructure

### Standard Workflow

1. Make changes to `.tf` files or `production.tfvars`
2. Run `terraform plan -var-file=environments/production.tfvars`
3. Review changes carefully
4. Run `terraform apply -var-file=environments/production.tfvars`

### Using GitHub Actions

The repository includes automated workflows:

- **terraform-plan.yml**: Runs on PRs, posts plan to PR comments
- **terraform-apply.yml**: Runs on merge to main, applies changes

Setup required:
1. Create AWS IAM role for GitHub Actions (OIDC)
2. Add role ARN to GitHub Secrets: `AWS_TERRAFORM_ROLE_ARN`
3. Configure environment protection rules in GitHub

## Disaster Recovery

### Database Backups

RDS automated backups:
- **Retention**: 30 days
- **Backup Window**: 03:00-04:00 UTC
- **Snapshots**: Taken daily

Restore from backup:
```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier <YOUR_RDS_INSTANCE>-restored \
  --db-snapshot-identifier <snapshot-id> \
  --region <AWS_REGION>
```

### State File Backups

S3 versioning is enabled on state bucket. To restore previous version:
```bash
aws s3api list-object-versions \
  --bucket <YOUR_STATE_BUCKET> \
  --prefix production/terraform.tfstate

aws s3api get-object \
  --bucket <YOUR_STATE_BUCKET> \
  --key production/terraform.tfstate \
  --version-id <version-id> \
  terraform.tfstate.backup
```

## Troubleshooting

### ECS Tasks Not Starting

```bash
# Check service events
aws ecs describe-services --cluster <YOUR_ECS_CLUSTER> --services <YOUR_ECS_SERVICE> --region <AWS_REGION> --query 'services[0].events'

# Check task logs
aws logs tail /ecs/<YOUR_ECS_LOG_GROUP> --follow --region <AWS_REGION>
```

### Database Connection Failures

```bash
# Verify security group rules
aws ec2 describe-security-groups --group-ids <rds-sg-id> --region <AWS_REGION>

# Test connectivity from ECS task
aws ecs execute-command \
  --cluster <YOUR_ECS_CLUSTER> \
  --task <task-arn> \
  --container app \
  --command "nc -zv <rds-endpoint> 5432" \
  --interactive \
  --region <AWS_REGION>
```

### High Costs

```bash
# Check cost breakdown
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE \
  --region <AWS_REGION>
```

## Module Structure

```
terraform/
├── backend.tf              # S3 state backend configuration
├── provider.tf             # AWS provider configuration
├── main.tf                 # Root module (orchestrates all modules)
├── variables.tf            # Global input variables
├── outputs.tf              # Global outputs
├── environments/
│   └── production.tfvars   # Production environment values
└── modules/
    ├── vpc/                # VPC, subnets, NAT gateway
    ├── security/           # IAM roles, security groups
    ├── rds/                # PostgreSQL database
    ├── elasticache/        # Redis cache
    ├── s3/                 # Storage buckets
    ├── alb/                # Application load balancer
    ├── ecs/                # Container orchestration
    └── monitoring/         # CloudWatch dashboard & alarms
```

## Security Best Practices

1. **Secrets**: All sensitive data stored in AWS Secrets Manager
2. **Encryption**: At rest and in transit for all data stores
3. **IAM**: Least-privilege access for all roles
4. **Security Groups**: Minimal port access, no 0.0.0.0/0 on private resources
5. **VPC**: Private subnets for all application components
6. **State Files**: Encrypted in S3, locked with DynamoDB
7. **Deletion Protection**: Enabled on production RDS and ALB

## Maintenance

### Regular Tasks

- **Weekly**: Review CloudWatch dashboard and alarms
- **Monthly**: Review cost reports and optimize
- **Quarterly**: Update Terraform and provider versions
- **Quarterly**: Review and rotate secrets
- **Annually**: Review disaster recovery procedures

### Updating Terraform

```bash
# Update provider versions in backend.tf
terraform init -upgrade

# Test with plan
terraform plan -var-file=environments/production.tfvars

# Apply updates
terraform apply -var-file=environments/production.tfvars
```

## Support

For issues or questions:
- Check CloudWatch logs and alarms
- Review Terraform plan output
- Consult AWS documentation
- Open GitHub issue

## License

Proprietary - CV-Tailor Project
