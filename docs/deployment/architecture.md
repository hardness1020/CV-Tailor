# Production Architecture

CV Tailor production infrastructure on AWS (us-west-1).

## Architecture Overview

```
                                   ┌─────────────────────┐
                                   │   Internet Users    │
                                   └──────────┬──────────┘
                                              │
                          ┌───────────────────┴────────────────────┐
                          │                                        │
                    HTTPS │                                        │ HTTP
                          │                                        │
               ┌──────────▼────────────┐              ┌───────────▼────────────┐
               │   CloudFront CDN      │              │   Application Load     │
               │  (Global Edge Cache)  │              │   Balancer (ALB)       │
               │                       │              │                        │
               │  ID: <CLOUDFRONT_DISTRIBUTION_ID>   │              │  cv-tailor-prod-alb    │
               └──────────┬────────────┘              └───────────┬────────────┘
                          │                                        │
                   OAC    │                             Health     │
                  Access  │                             Checks     │
                          │                              (:80)     │
               ┌──────────▼────────────┐              ┌───────────▼────────────┐
               │   S3 Bucket           │              │   ECS Fargate          │
               │  (Private)            │              │   (Serverless)         │
               │                       │              │                        │
               │  cv-tailor-prod-      │              │  Cluster: cv-tailor-   │
               │  frontend/            │              │  production-cluster    │
               │                       │              │                        │
               │  • index.html         │              │  Service: 2 tasks      │
               │  • assets/            │              │  (Gunicorn + Django)   │
               │  • *.js, *.css        │              └───────────┬────────────┘
               └───────────────────────┘                          │
                                                                  │
                                          ┌───────────────────────┼────────────────────┐
                                          │                       │                    │
                                   ┌──────▼────────┐   ┌─────────▼────────┐  ┌────────▼──────────┐
                                   │  RDS          │   │  ElastiCache     │  │  ECR              │
                                   │  PostgreSQL   │   │  Redis           │  │  Docker Registry  │
                                   │               │   │                  │  │                   │
                                   │  • Database   │   │  • Cache         │  │  • Backend image  │
                                   │  • Persistent │   │  • Celery broker │  │    (294MB)        │
                                   └───────────────┘   └──────────────────┘  └───────────────────┘
```

## Component Details

### Frontend Layer

#### CloudFront Distribution
- **Distribution ID**: <CLOUDFRONT_DISTRIBUTION_ID>
- **Domain**: <YOUR_CLOUDFRONT_DOMAIN>
- **Purpose**: Global CDN for HTTPS delivery and edge caching
- **Features**:
  - Automatic HTTPS with AWS managed certificate
  - Global edge locations for low latency
  - Origin Access Control (OAC) for S3 security
  - Custom error response: 404 → /index.html (React Router support)
  - Compression enabled (gzip/brotli)
- **Cache Policy**: CachingOptimized (658327ea-f89d-4fab-a63d-7e88639e58f6)
- **Viewer Protocol**: Redirect HTTP to HTTPS

#### S3 Bucket (Frontend Storage)
- **Bucket Name**: <YOUR_S3_BUCKET>
- **Region**: us-west-1
- **Access**: Private (CloudFront OAC only)
- **Contents**:
  - React SPA build artifacts
  - Static assets (JS, CSS, images)
  - index.html (entry point)
- **Size**: ~736 KB (production build)

### Backend Layer

#### Application Load Balancer (ALB)
- **Name**: <YOUR_ALB_NAME>
- **DNS**: <YOUR_ALB_DNS>
- **Scheme**: Internet-facing
- **Protocol**: HTTP (HTTPS not configured yet)
- **Target Group**: <YOUR_TARGET_GROUP>
- **Health Check**:
  - Path: `/health/`
  - Protocol: HTTP
  - Interval: 30 seconds
  - Timeout: 5 seconds
  - Healthy threshold: 3
  - Unhealthy threshold: 3

#### ECS Fargate (Container Orchestration)
- **Cluster**: <YOUR_ECS_CLUSTER>
- **Service**: <YOUR_ECS_SERVICE>
- **Launch Type**: FARGATE (serverless containers)
- **Desired Tasks**: 2
- **Task Definition**: <YOUR_ECS_TASK_DEFINITION> (latest revision)
- **Networking**: VPC with public subnets
- **Security Group**: Allows inbound on port 8000 from ALB

**Task Configuration**:
- **CPU**: 512 (0.5 vCPU)
- **Memory**: 1024 MB (1 GB)
- **Container Port**: 8000
- **Platform**: linux/amd64
- **Health Check**:
  - Command: `curl -f http://localhost:8000/health/ || exit 1`
  - Start Period: 180 seconds (3 minutes grace period)
  - Interval: 30 seconds
  - Timeout: 5 seconds
  - Retries: 3

**Environment Variables** (from Secrets Manager):
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: ElastiCache Redis connection string
- `SECRET_KEY`: Django secret key
- `ALLOWED_HOSTS`: ALB DNS name
- `CORS_ALLOWED_ORIGINS`: CloudFront domain
- `OPENAI_API_KEY`: LLM service credentials

#### Container Image (ECR)
- **Repository**: <AWS_ACCOUNT_ID>.dkr.ecr.us-west-1.amazonaws.com/cv-tailor/production
- **Image Tag**: latest
- **Size**: 294MB compressed (optimized from 4.55GB)
- **Base Image**: python:3.11-slim-bookworm
- **Build Strategy**: Multi-stage (builder + runtime)
- **Server**: Gunicorn 21.2.0 with 2 workers

**Optimization Details**:
- Removed `unstructured[pdf]` (saved ~4GB from torch/transformers)
- Multi-stage build separates compilation from runtime
- Direct Gunicorn execution (not `uv run` wrapper)
- Minimal runtime dependencies (libpq5, libmagic1, poppler-utils)

### Data Layer

#### RDS PostgreSQL
- **Engine**: PostgreSQL 15+
- **Instance Class**: (check AWS console for details)
- **Multi-AZ**: Production deployment
- **Storage**: Encrypted at rest
- **Backups**: Automated daily backups
- **Purpose**: Persistent relational data (users, artifacts, CVs)

#### ElastiCache Redis
- **Engine**: Redis
- **Purpose**:
  - Application cache (session data, query caching)
  - Celery message broker (async task queue)
- **Encryption**: In-transit and at-rest

### Supporting Services

#### AWS Secrets Manager
- Stores sensitive configuration:
  - Database credentials
  - Redis authentication
  - API keys (OpenAI)
  - Django secret key
- Automatic rotation enabled (where applicable)
- Accessed by ECS tasks via IAM roles

#### CloudWatch Logs
- **Log Group**: <YOUR_LOG_GROUP>
- **Retention**: 7 days (configurable)
- **Contents**:
  - Gunicorn access logs
  - Django application logs
  - Container startup logs
  - Error traces

#### IAM Roles
- **ECS Task Execution Role**: Pull ECR images, write CloudWatch logs
- **ECS Task Role**: Access Secrets Manager, S3, other AWS services

## Network Architecture

### VPC Configuration
- **Region**: us-west-1 (N. California)
- **Availability Zones**: Multi-AZ deployment
- **Subnets**:
  - Public subnets: ALB, NAT Gateway
  - Private subnets: ECS tasks, RDS, ElastiCache
- **Internet Gateway**: Enables outbound internet access
- **NAT Gateway**: Private subnet internet access

### Security Groups

**ALB Security Group**:
- Inbound: 80 (HTTP) from 0.0.0.0/0
- Outbound: 8000 to ECS tasks

**ECS Security Group**:
- Inbound: 8000 from ALB security group
- Outbound: 443 (HTTPS) for API calls, 5432 (PostgreSQL), 6379 (Redis)

**RDS Security Group**:
- Inbound: 5432 from ECS security group
- Outbound: None required

**ElastiCache Security Group**:
- Inbound: 6379 from ECS security group
- Outbound: None required

## Traffic Flow

### Frontend Request Flow
1. User visits `https://<YOUR_CLOUDFRONT_DOMAIN>`
2. CloudFront checks edge cache for requested file
3. If cache miss, CloudFront fetches from S3 via OAC
4. S3 returns file (authenticated via OAC)
5. CloudFront caches and returns to user
6. Browser loads React SPA
7. React Router handles client-side routing

### Backend API Request Flow
1. Frontend makes API call to `http://<YOUR_ALB_DNS>/api/...`
2. ALB receives request and performs health checks on targets
3. ALB routes to healthy ECS task via round-robin
4. Gunicorn worker processes Django request
5. Django accesses PostgreSQL (data) and Redis (cache)
6. Response returned through ALB to frontend
7. Frontend updates UI

### Deployment Flow
1. Developer builds Docker image locally (linux/amd64)
2. Image tagged and pushed to ECR
3. ECS service updated with `--force-new-deployment`
4. ECS pulls new image from ECR
5. New tasks started (2 new tasks)
6. Health checks performed (180s grace period)
7. Once healthy, ALB routes traffic to new tasks
8. Old tasks drained and stopped
9. Deployment complete (zero downtime)

## Scalability

### Current Capacity
- **Frontend**: Unlimited (CloudFront + S3 auto-scale)
- **Backend**: 2 ECS tasks (can handle ~100 concurrent requests)
- **Database**: Single RDS instance (vertical scaling available)
- **Cache**: Single ElastiCache node (cluster mode available)

### Scaling Strategy

**Horizontal Scaling** (increase tasks):
```bash
aws ecs update-service \
  --cluster <YOUR_ECS_CLUSTER> \
  --service <YOUR_ECS_SERVICE> \
  --desired-count 4 \
  --region us-west-1
```

**Auto-scaling** (future enhancement):
- ECS Service Auto Scaling based on CPU/memory
- Target tracking: 70% CPU utilization
- Scale out: +1 task per 10% over target
- Scale in: -1 task per 10% under target

**Database Scaling**:
- Vertical: Increase RDS instance class
- Horizontal: Read replicas for read-heavy workloads

## Cost Optimization

### Current Costs (Estimated)
- **ECS Fargate**: 2 tasks × 0.5 vCPU × 1GB RAM = ~$30/month
- **ALB**: ~$20/month (includes LCUs)
- **RDS**: ~$30-50/month (db.t3.micro or db.t3.small)
- **ElastiCache**: ~$20/month (cache.t3.micro)
- **CloudFront**: ~$5/month (low traffic)
- **S3**: ~$1/month (minimal storage)
- **ECR**: ~$1/month (image storage)
- **Data Transfer**: ~$5-10/month
- **Total**: ~$120-150/month

### Cost Savings
- Removed 4GB of unnecessary ML dependencies (Docker image size)
- Fargate Spot (future): 70% savings on compute
- Reserved Instances (RDS): 30-60% savings for committed usage
- S3 Intelligent-Tiering: Automatic cost optimization

## High Availability

### Current HA Features
- **Multi-AZ RDS**: Automatic failover to standby
- **ECS Multi-task**: 2 tasks across availability zones
- **ALB Health Checks**: Automatic traffic routing to healthy tasks
- **CloudFront**: Global edge locations with automatic failover

### Single Points of Failure
- ⚠️ Single ElastiCache node (no automatic failover)
- ⚠️ Single ALB (99.99% SLA, but no redundancy)

### Future HA Enhancements
- ElastiCache cluster mode (automatic failover)
- Multi-region deployment (disaster recovery)
- Route 53 health checks with failover routing

## Security

### Data in Transit
- ✅ CloudFront → User: HTTPS (TLS 1.2+)
- ⚠️ Browser → ALB: HTTP (HTTPS not configured)
- ✅ ALB → ECS: HTTP (internal VPC)
- ✅ ECS → RDS: Encrypted PostgreSQL connection
- ✅ ECS → ElastiCache: Encrypted Redis connection

### Data at Rest
- ✅ S3: Default encryption (AES-256)
- ✅ RDS: Encrypted storage
- ✅ ElastiCache: Encrypted storage
- ✅ ECR: Encrypted image storage
- ✅ Secrets Manager: Encrypted secrets

### Access Control
- ✅ S3: Private bucket with CloudFront OAC only
- ✅ ECS: IAM roles with least privilege
- ✅ RDS: Security group restricts to ECS only
- ✅ ElastiCache: Security group restricts to ECS only
- ✅ Secrets Manager: IAM role-based access

### Future Security Enhancements
- Configure HTTPS on ALB (ACM certificate)
- WAF on CloudFront (DDoS protection, rate limiting)
- GuardDuty (threat detection)
- AWS Config (compliance monitoring)

## Monitoring and Logging

### Available Logs
- **ECS Logs**: CloudWatch Logs `<YOUR_LOG_GROUP>`
- **ALB Access Logs**: (enable in S3 for analysis)
- **CloudFront Logs**: (enable for CDN analytics)

### Metrics
- **ECS**: CPU, memory, task count
- **ALB**: Request count, latency, error rate, target health
- **RDS**: CPU, connections, storage, IOPS
- **ElastiCache**: CPU, memory, evictions, connections

### Alerting (Future)
- CloudWatch Alarms on critical metrics
- SNS notifications for deployment events
- PagerDuty integration for on-call

## Disaster Recovery

### Backup Strategy
- **RDS**: Automated daily backups (7-day retention)
- **Code**: Git repository (GitHub)
- **Infrastructure**: Manual ECR image tags for rollback
- **Configuration**: Secrets Manager versioning

### Recovery Procedures
- **Code Rollback**: See [Deployment Pipeline](./deployment-pipeline.md)
- **Database Recovery**: RDS point-in-time restore (up to 7 days)
- **Infrastructure Recovery**: Re-deploy from Git + ECR

### Recovery Time Objective (RTO)
- Frontend: ~5 minutes (CloudFront invalidation)
- Backend: ~10 minutes (ECS task replacement)
- Database: ~30 minutes (RDS restore)

### Recovery Point Objective (RPO)
- Database: Up to 5 minutes (RDS automated backups)
- Application Code: 0 (Git repository)

## References

- [Current Deployment Status](./current-deployment.md)
- [Deployment Pipeline](./deployment-pipeline.md)
- [Troubleshooting Guide](./troubleshooting.md)
