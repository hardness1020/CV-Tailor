# ADR-030: AWS Deployment Architecture for Production

**File:** `docs/adrs/adr-030-aws-deployment-architecture.md`
**Status:** Accepted
**Date:** 2025-10-20
**Deciders:** DevOps Team, Engineering Manager, CTO
**Related Documents:**
- Discovery: `disc-001-environment-config-analysis.md`
- TECH SPEC: `spec-deployment-v1.0.md` (detailed service specifications)
- ADR-029: Multi-Environment Settings Architecture

---

## Context

CV-Tailor currently runs on Docker Compose for local development. We need a production-ready cloud infrastructure to deploy the application for real users.

**Current State:**
- Docker Compose with 5 containers: PostgreSQL, Redis, Backend, Celery, Frontend
- Local storage for media files (`/app/media/`)
- WhiteNoise for static files
- No production deployment exists

**Requirements:**
- **Initial Scale:** 10-30 users
- **Growth Target:** Scale to 1000+ users without architecture changes (only configuration)
- **Budget:** $80-150/month initially
- **Availability:** 99.5% (can upgrade to 99.9% multi-AZ later)
- **Deployment Time:** < 5 minutes (automated CI/CD)
- **Security:** Industry standard (encryption, secrets management, network isolation)
- **Compliance:** Data encryption at rest and in transit

**Constraints:**
- Team has limited DevOps experience (need managed services)
- Small team (need minimal operational overhead)
- Cost-sensitive (startup budget)
- Must support current Docker-based workflow (ECS Fargate preferred)

---

## Decision

**Deploy to Amazon Web Services (AWS) using a right-sized, managed services architecture:**

### Core Services

**1. ECS Fargate (Compute):**
- Backend service: 1-3 tasks @ 0.5 vCPU, 1GB RAM
- Celery worker: 1-2 tasks @ 0.25 vCPU, 0.5GB RAM
- Auto-scaling based on CPU (70% threshold)
- **Why:** Serverless containers, no EC2 management, pay-per-use

**2. RDS PostgreSQL (Database):**
- Instance: db.t4g.micro (2 vCPU, 1GB RAM)
- Storage: 20GB GP3 SSD, auto-scales to 100GB
- Single-AZ initially (Multi-AZ when revenue permits)
- 7-day automated backups
- **Why:** Managed backups, automated patching, encryption at rest

**3. ElastiCache Redis (Cache & Broker):**
- Instance: cache.t4g.micro (2 vCPU, 0.5GB RAM)
- Single node initially (cluster mode for HA later)
- **Why:** Managed service, automatic failover (when multi-node), compatible with existing Redis code

**4. Application Load Balancer (Networking):**
- HTTPS termination with ACM certificate
- Health checks (/ health endpoint)
- Auto-scales with backend tasks
- **Why:** SSL offloading, path-based routing, seamless ECS integration

**5. S3 (Storage):**
- Static files bucket (public read)
- Media files bucket (private, signed URLs)
- Terraform state bucket (versioned)
- **Why:** Unlimited scalability, encryption, lifecycle policies, 11 9's durability

**6. Secrets Manager (Secrets):**
- Application secrets (SECRET_KEY, OPENAI_API_KEY, OAuth credentials)
- Database credentials (with automatic rotation)
- **Why:** Automatic rotation, audit logging, fine-grained access control

**7. CloudWatch (Monitoring):**
- Application logs (7-day retention)
- Metrics (CPU, memory, request count)
- Alarms (high CPU, error rate, budget)
- **Why:** Native AWS integration, cost-effective, real-time monitoring

**8. Route 53 (DNS) + ACM (SSL):**
- DNS hosting for cv-tailor.com
- Free SSL certificate (auto-renewal)
- **Why:** Seamless AWS integration, free certificates

### Network Architecture

**VPC Configuration:**
- Region: us-west-1 (N. California - low latency for target users)
- CIDR: 10.0.0.0/16
- Availability Zone: us-west-1a (single-AZ for cost, add 1b later)

**Subnets:**
- Public subnet (10.0.1.0/24): ALB, NAT Gateway
- Private subnet (10.0.11.0/24): ECS tasks
- Private subnet (10.0.21.0/24): RDS, ElastiCache

**Security Groups (Least Privilege):**
- ALB: Allow 80/443 from internet → Forward to ECS on 8000
- ECS: Allow 8000 from ALB only → Allow outbound to RDS, Redis, HTTPS APIs
- RDS: Allow 5432 from ECS only
- ElastiCache: Allow 6379 from ECS only

### Infrastructure as Code

**Terraform for all infrastructure:**
- State stored in S3 (with versioning and DynamoDB locking)
- Modular structure (VPC, ECS, RDS, ElastiCache, S3, Secrets)
- Environment-specific variable files (`staging.tfvars`, `production.tfvars`)
- **Why:** Version control, reproducible infrastructure, disaster recovery

### Deployment Pipeline

**CI/CD with GitHub Actions:**
1. **CI Pipeline** (on PR): Run tests, linting, security scan
2. **Staging Deployment** (on merge to main): Auto-deploy to staging
3. **Production Deployment** (manual approval): Deploy to production

---

## Consequences

### Positive

1. **✅ Scalability:**
   - Horizontally scale ECS tasks (1 → 10 tasks with configuration change)
   - Vertically scale RDS instance type (micro → xlarge with ~1 hour downtime)
   - No architecture changes needed to support 1000+ users

2. **✅ Reliability:**
   - Automated backups (RDS: 7 days, S3: versioned)
   - Auto-recovery (ECS restarts failed tasks)
   - Health checks (ALB marks unhealthy tasks)
   - Multi-AZ upgrade path (when budget permits)

3. **✅ Security:**
   - Network isolation (private subnets for app tier and data tier)
   - Encryption at rest (RDS, S3, ElastiCache)
   - Encryption in transit (HTTPS, TLS to RDS/Redis)
   - Secrets rotation (automatic for DB, manual for API keys)
   - IAM roles (no long-lived credentials)

4. **✅ Operational Simplicity:**
   - Managed services (no server patching)
   - Auto-scaling (hands-off during traffic spikes)
   - CloudWatch alarms (proactive issue detection)
   - Low DevOps overhead

5. **✅ Cost Efficiency:**
   - Right-sized instances ($84/month base cost)
   - Pay-per-use (Fargate only charges for running tasks)
   - No over-provisioning (auto-scaling prevents waste)
   - Free tier eligible services (ALB, CloudWatch to some extent)

6. **✅ Developer Experience:**
   - Same Docker images used locally and in production
   - Terraform modules match docker-compose services
   - Environment parity (staging mirrors production)
   - Fast deployments (< 5 minutes)

7. **✅ Compliance Ready:**
   - Encryption at rest and in transit (meets most compliance requirements)
   - Audit logging (CloudTrail for API calls, CloudWatch for application)
   - Data residency (all data in us-west-1)
   - Backup retention policies

### Negative

1. **❌ AWS Lock-in:**
   - ECS Fargate is AWS-specific (not portable to GCP/Azure)
   - Terraform helps but migration still requires rewriting infrastructure code
   - RDS, ElastiCache are managed services (harder to migrate than self-managed)

2. **❌ Cost Unpredictability:**
   - Fargate costs scale with task count (can spike during traffic)
   - Data transfer costs hard to predict
   - OpenAI API costs are variable (main cost driver)
   - Need billing alerts ($120/month threshold)

3. **❌ Learning Curve:**
   - Team needs to learn Terraform (new skill)
   - AWS console complexity (many services to navigate)
   - IAM permissions can be tricky (least privilege requires planning)
   - Debugging distributed systems harder than local Docker

4. **❌ Single-AZ Risk:**
   - Availability Zone failure affects service (rare but possible)
   - ~99.5% availability vs 99.99% multi-AZ
   - Acceptable for MVP, must upgrade for SLA commitments

5. **❌ Initial Setup Effort:**
   - Terraform modules take time to write (~5 days)
   - DNS/SSL setup requires domain verification
   - Secrets migration (from `.env` to Secrets Manager)
   - Testing staging environment before production

### Mitigation

- **Lock-in:** Abstract cloud provider behind Django storage backends (django-storages)
- **Costs:** CloudWatch billing alarms, daily cost review, auto-scaling limits
- **Learning:** Comprehensive documentation (OP-NOTE), staging environment for experimentation
- **Single-AZ:** Plan multi-AZ upgrade when revenue > $1000/month
- **Setup Effort:** Detailed implementation guide, reusable Terraform modules

---

## Alternatives Considered

### Alternative 1: Platform-as-a-Service (Railway, Render, Fly.io)

**Pros:**
- ✅ Fastest deployment (< 1 day)
- ✅ No Terraform needed (web UI configuration)
- ✅ Automatic SSL, domain setup
- ✅ Good developer experience

**Cons:**
- ❌ Higher cost ($50-100/month for equivalent resources)
- ❌ Less control over infrastructure
- ❌ Scaling limitations (harder to customize)
- ❌ Vendor lock-in (harder to migrate than AWS)

**Decision:** Rejected for production, but good for rapid prototyping

### Alternative 2: Google Cloud Platform (GCP)

**Services:** Cloud Run, Cloud SQL, Memorystore, Cloud Storage

**Pros:**
- ✅ Similar managed services to AWS
- ✅ Excellent for containers (Cloud Run is simpler than ECS)
- ✅ Competitive pricing
- ✅ Good Terraform support

**Cons:**
- ❌ Team has AWS experience (smaller learning curve)
- ❌ Fewer third-party integrations
- ❌ Cloud Run has cold start issues (not ideal for Django)

**Decision:** Rejected, but good alternative if AWS becomes limiting

### Alternative 3: Self-Managed Kubernetes (EKS, GKE, or self-hosted)

**Pros:**
- ✅ Most flexible and portable
- ✅ Industry standard (widely documented)
- ✅ Multi-cloud capable

**Cons:**
- ❌ Massive overkill for 10-30 users
- ❌ High operational complexity (control plane management)
- ❌ Steep learning curve
- ❌ EKS costs $0.10/hour just for control plane ($73/month before workloads)

**Decision:** Rejected, reconsider at 10,000+ users

### Alternative 4: EC2 Instances with Docker Compose

**Pros:**
- ✅ Familiar workflow (same as local dev)
- ✅ Full control over instances
- ✅ Lower cost (EC2 reserved instances)

**Cons:**
- ❌ Manual server management (patching, monitoring)
- ❌ No auto-scaling (manual intervention)
- ❌ Single point of failure (one EC2 instance)
- ❌ Requires DevOps expertise

**Decision:** Rejected, we need managed services

### Alternative 5: Serverless (Lambda Functions)

**Pros:**
- ✅ Ultimate scalability (to zero)
- ✅ Pay-per-request (lowest cost for low traffic)
- ✅ No server management

**Cons:**
- ❌ Django doesn't fit serverless model well
- ❌ Cold start latency (bad UX)
- ❌ Complex architecture (API Gateway, Lambda, RDS Proxy)
- ❌ Requires major code refactoring

**Decision:** Rejected, not suitable for Django monolith

---

## Rollback Plan

**If AWS deployment fails or has critical issues:**

### Scenario 1: Infrastructure provisioning fails

**Recovery:**
1. Fix Terraform errors
2. `terraform destroy` (clean up partial resources)
3. Re-run `terraform apply` with corrections
4. Cost: Only for resources that were provisioned (minimal)

### Scenario 2: Deployment works but application has critical bugs

**Recovery:**
1. Rollback ECS task definition to previous revision:
   ```bash
   aws ecs update-service --service backend --task-definition backend:PREVIOUS_VERSION
   ```
2. Verify health checks pass
3. Debug issue in staging environment
4. Cost: None (just redeploy)

### Scenario 3: AWS costs exceed budget

**Recovery:**
1. Reduce ECS task count to 1
2. Downgrade RDS to db.t4g.micro (if upgraded)
3. Remove unnecessary CloudWatch metrics
4. Set strict auto-scaling limits
5. Cost reduction: ~30-40%

### Scenario 4: Need to migrate off AWS completely

**Recovery:**
1. Export database:
   ```bash
   pg_dump -h <RDS_ENDPOINT> > backup.sql
   ```
2. Download media files from S3:
   ```bash
   aws s3 sync s3://cv-tailor-prod-media ./media/
   ```
3. Deploy to alternative platform (Railway, Render)
4. Restore database and files
5. Update DNS
6. Time: 4-6 hours
7. Cost: Double infrastructure cost during migration period

**Data Protection:**
- ✅ Daily RDS snapshots (7-day retention)
- ✅ S3 versioning enabled
- ✅ Terraform state versioned (can recreate infrastructure)
- ✅ Database restoration tested in staging

---

## Cost Analysis

### Initial Cost (10-30 users): $84/month

| Category | Monthly Cost |
|----------|--------------|
| **Compute** (ECS Fargate) | $22 |
| **Database** (RDS PostgreSQL t4g.micro) | $16 |
| **Cache** (ElastiCache Redis t4g.micro) | $12 |
| **Networking** (ALB) | $21 |
| **Storage** (S3) | $0.25 |
| **Monitoring** (CloudWatch) | $7 |
| **Secrets** (Secrets Manager) | $0.85 |
| **DNS** (Route 53) | $0.90 |
| **SSL** (ACM) | $0 (free) |
| **Variable** (OpenAI API) | $10-50 |
| **Total** | **$90-130/month** |

### Scaling Projections

| Users | Monthly Cost | Changes |
|-------|--------------|---------|
| 10-30 | $90-130 | Base configuration |
| 50 | $120-160 | +1 backend task |
| 100 | $200-250 | Upgrade RDS to t4g.small, +2 backend tasks, CloudFront CDN |
| 500 | $500-600 | Upgrade RDS to r6g.large + Multi-AZ, ElastiCache cluster, 5-7 backend tasks |
| 1000 | $1000-1200 | RDS xlarge + Multi-AZ + read replicas, 10-15 backend tasks |

**Cost Optimization Strategies:**
- Use Fargate Spot for Celery workers (70% savings)
- RDS reserved instances (40% savings after 1 year)
- S3 Intelligent-Tiering (automatic cost optimization)
- CloudWatch Logs retention: 3 days (reduce storage)

---

## Security Considerations

**Network Security:**
- ✅ Private subnets for all application and data tiers
- ✅ Security groups with least privilege
- ✅ No public IPs on ECS tasks or RDS
- ✅ NAT Gateway for outbound internet (ECS needs to call OpenAI API)

**Data Security:**
- ✅ Encryption at rest (RDS, S3, ElastiCache, EBS)
- ✅ Encryption in transit (TLS 1.3 for HTTPS, SSL to RDS, TLS to Redis)
- ✅ Secrets Manager (encrypted with KMS)
- ✅ S3 bucket policies (block public access on media bucket)

**Access Control:**
- ✅ IAM roles for ECS tasks (no long-lived keys)
- ✅ Principle of least privilege (each service has minimal permissions)
- ✅ MFA required for AWS console access
- ✅ CloudTrail logging (audit all API calls)

**Application Security:**
- ✅ Django security middleware (from ADR-029 production settings)
- ✅ Rate limiting (100/day anon, 1000/day user)
- ✅ CORS restricted to cv-tailor.com
- ✅ HSTS headers (1-year max-age)

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- Create Terraform modules (VPC, IAM roles)
- Set up S3 backend for Terraform state
- Provision staging environment
- Test infrastructure provisioning

### Phase 2: Core Services (Week 2)
- Provision RDS PostgreSQL
- Provision ElastiCache Redis
- Provision ECS cluster and task definitions
- Provision ALB with target groups
- Test backend deployment to staging

### Phase 3: Storage & Secrets (Week 2)
- Create S3 buckets
- Migrate secrets to Secrets Manager
- Configure django-storages for S3
- Test file uploads to staging

### Phase 4: CI/CD (Week 3)
- Set up GitHub Actions workflows
- Configure ECR (container registry)
- Automate deployments to staging
- Test CI/CD pipeline

### Phase 5: Production (Week 3-4)
- Provision production environment
- DNS and SSL setup
- Deploy to production
- Run smoke tests
- Monitor for 24 hours

---

## Success Metrics

**Performance:**
- [ ] API latency p95 < 500ms
- [ ] API latency p99 < 1000ms
- [ ] CV generation time < 30 seconds
- [ ] Health check response < 200ms

**Reliability:**
- [ ] Availability > 99.5%
- [ ] Zero data loss
- [ ] Recovery time < 15 minutes (for single-AZ failure)
- [ ] Successful backups daily

**Cost:**
- [ ] Monthly cost < $150 (for 10-30 users)
- [ ] No surprise bills (billing alarms work)
- [ ] Auto-scaling prevents over-provisioning

**Security:**
- [ ] No production secrets in code or logs
- [ ] All data encrypted at rest
- [ ] All connections use TLS
- [ ] Security group rules reviewed (least privilege)

**Operations:**
- [ ] Deployment time < 5 minutes
- [ ] Zero-downtime deployments
- [ ] Rollback time < 2 minutes
- [ ] Monitoring alerts work (tested)

---

## Future Enhancements

**Short-term (3-6 months):**
- [ ] CloudFront CDN for static files (reduce latency globally)
- [ ] Multi-AZ RDS (99.99% availability)
- [ ] ElastiCache cluster mode (high availability)
- [ ] Sentry integration (error tracking)

**Medium-term (6-12 months):**
- [ ] Read replicas for RDS (scale reads)
- [ ] Multi-region deployment (disaster recovery)
- [ ] AWS WAF (Web Application Firewall)
- [ ] Lambda@Edge for edge computing

**Long-term (12+ months):**
- [ ] Aurora Serverless v2 (auto-scaling database)
- [ ] Active-active multi-region (global availability)
- [ ] Kubernetes migration (if scale requires)

---

## Related ADRs

**Depends on:**
- ADR-029: Multi-Environment Settings (production settings for AWS)

**Influences:**
- ADR-031: Secrets Management Strategy (AWS Secrets Manager)
- ADR-0XX: CI/CD Pipeline (GitHub Actions deploy to AWS)

**Related:**
- ADR-005: Backend Framework (Django on AWS ECS)
- ADR-006: Database Choice (PostgreSQL on RDS)

---

## References

**AWS Documentation:**
- [ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [RDS Security](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.html)
- [Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

**Terraform:**
- [AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

**Django Deployment:**
- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [django-storages S3 Backend](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html)

**Internal:**
- TECH SPEC: `docs/specs/spec-deployment-v1.0.md` (detailed specifications)
- Discovery: `docs/discovery/disc-001-environment-config-analysis.md`

---

## Approval

**Reviewed by:**
- [x] DevOps Team Lead - Approved
- [x] Engineering Manager - Approved (budget approved: $150/month)
- [ ] Security Team - Pending review
- [x] CTO - Approved

**Approved for implementation:** Yes (pending security review)

**Implementation Owner:** DevOps Team

**Target Completion:** Week 3 of deployment project

**Budget Approved:** $150/month initial, $500/month at 100 users
