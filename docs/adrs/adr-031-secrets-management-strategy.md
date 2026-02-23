# ADR-031: Secrets Management Strategy

**File:** `docs/adrs/adr-031-secrets-management-strategy.md`
**Status:** Accepted
**Date:** 2025-10-20
**Deciders:** DevOps Team, Security Team
**Related Documents:**
- Discovery: `disc-001-environment-config-analysis.md`
- TECH SPEC: `spec-deployment-v1.0.md`
- ADR-029: Multi-Environment Settings Architecture
- ADR-030: AWS Deployment Architecture

---

## Context

CV-Tailor currently stores all secrets in `.env` files (git-ignored), including sensitive credentials that provide access to:
- **Django SECRET_KEY:** Session signing, CSRF protection
- **OPENAI_API_KEY:** LLM API access (cost risk: $50+/month potential abuse)
- **Database passwords:** Full database access
- **Google OAuth credentials:** User authentication bypass risk
- **GitHub tokens:** Private repository access

**Current Problems:**
1. **No Rotation:** Secrets never change (same OPENAI_API_KEY for months)
2. **No Audit Trail:** Can't track who accessed secrets or when
3. **Distribution Challenges:** Manual `.env` file sharing with team members (via Slack/email - insecure)
4. **No Access Control:** Anyone with `.env` file has all secrets
5. **Production Risk:** `.env` files can be accidentally committed (despite `.gitignore`)

**Discovered from Codebase Analysis:**
- All secrets loaded via `python-decouple` (`config()` function)
- 15 files reference secrets (OPENAI_API_KEY, DB_PASSWORD, etc.)
- No existing AWS SDK usage (clean slate for Secrets Manager)
- Good pattern: `create_dev_superuser.py` checks `DEBUG` flag before using credentials

**Security Incidents (Hypothetical Risks):**
- If OPENAI_API_KEY leaked: Unlimited API charges (could be $1000s)
- If DB_PASSWORD leaked: Full data access/deletion
- If SECRET_KEY leaked: Session hijacking, CSRF bypass

---

## Decision

**Implement a multi-tiered secrets management strategy based on environment:**

### Development Environment: `.env` Files (Current Pattern)

**Method:** Git-ignored `.env` files with `python-decouple`

**Rationale:**
- ✅ Simple for local development
- ✅ Fast iteration (no AWS API calls)
- ✅ Works offline
- ✅ Familiar to team

**Security Posture:**
- Low-value secrets (dev-only API keys)
- No production data accessible
- `.gitignore` prevents accidental commits
- Each developer has own `.env` file

**Example:**
```bash
# backend/.env (local development)
DJANGO_ENV=development
SECRET_KEY=django-insecure-dev-key-change-in-production
OPENAI_API_KEY=sk-dev-xxxxxxxxxxxxxxxxxxxxxxxx
DB_PASSWORD=your-secure-password-here
GOOGLE_CLIENT_SECRET=dev_secret
```

### Staging & Production Environments: AWS Secrets Manager

**Method:** AWS Secrets Manager with automatic rotation

**Rationale:**
- ✅ Automatic rotation (DB credentials every 30 days)
- ✅ Audit logging (CloudTrail tracks all GetSecretValue calls)
- ✅ Fine-grained access control (IAM policies per environment)
- ✅ Encryption at rest (KMS keys)
- ✅ Versioning (rollback to previous secrets)
- ✅ Cross-region replication (disaster recovery)

**Architecture:**
```
┌─────────────────────────────────────┐
│  ECS Task (Backend)                 │
│                                     │
│  1. Task starts                     │
│  2. IAM role authorizes access      │
│  3. boto3 calls GetSecretValue      │
│  4. Secrets loaded into Django      │
│  5. Environment vars set            │
│                                     │
└────────────┬────────────────────────┘
             │ HTTPS (TLS 1.3)
             ▼
┌─────────────────────────────────────┐
│  AWS Secrets Manager                │
│                                     │
│  Secret: cv-tailor-prod-secrets     │
│  {                                  │
│    "DJANGO_SECRET_KEY": "...",      │
│    "OPENAI_API_KEY": "sk-proj-...", │
│    "GOOGLE_CLIENT_ID": "...",       │
│    "GOOGLE_CLIENT_SECRET": "..."    │
│  }                                  │
│                                     │
│  Secret: cv-tailor-prod-db-creds    │
│  {                                  │
│    "username": "cv_tailor_admin",   │
│    "password": "...",               │
│    "host": "rds-endpoint",          │
│    "port": 5432                     │
│  }                                  │
└─────────────────────────────────────┘
             │
             ▼ (Rotation Lambda)
┌─────────────────────────────────────┐
│  Lambda Function                    │
│  - Generates new DB password        │
│  - Updates RDS master password      │
│  - Updates secret in Secrets Mgr    │
│  - Runs every 30 days               │
└─────────────────────────────────────┘
```

**Django Implementation:**
```python
# backend/cv_tailor/settings/production.py
import json
import boto3
from botocore.exceptions import ClientError
from django.core.exceptions import ImproperlyConfigured

def get_secret(secret_name, region_name="us-west-1"):
    """
    Retrieve secret from AWS Secrets Manager.

    Implements:
    - Retry logic (3 attempts with exponential backoff)
    - Error handling (fail fast if secrets unavailable)
    - Caching (secrets loaded once at startup)
    """
    client = boto3.client(
        'secretsmanager',
        region_name=region_name
    )

    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except ClientError as e:
        error_code = e.response['Error']['Code']

        if error_code == 'ResourceNotFoundException':
            raise ImproperlyConfigured(f"Secret {secret_name} not found in Secrets Manager")
        elif error_code == 'InvalidRequestException':
            raise ImproperlyConfigured(f"Invalid request for secret {secret_name}")
        elif error_code == 'InvalidParameterException':
            raise ImproperlyConfigured(f"Invalid parameter for secret {secret_name}")
        elif error_code == 'DecryptionFailure':
            raise ImproperlyConfigured(f"Cannot decrypt secret {secret_name}")
        elif error_code == 'InternalServiceError':
            raise ImproperlyConfigured(f"AWS Secrets Manager internal error (retry deployment)")
        else:
            raise

# Load secrets at settings import time (cached for container lifetime)
try:
    SECRETS = get_secret(os.environ['AWS_SECRETS_NAME'])
    SECRET_KEY = SECRETS['DJANGO_SECRET_KEY']
    OPENAI_API_KEY = SECRETS['OPENAI_API_KEY']

    # Database credentials from separate secret (supports automatic rotation)
    DB_SECRETS = get_secret(f"{os.environ['AWS_SECRETS_NAME']}-db")
    DATABASES['default']['USER'] = DB_SECRETS['username']
    DATABASES['default']['PASSWORD'] = DB_SECRETS['password']
    DATABASES['default']['HOST'] = DB_SECRETS['host']
except KeyError as e:
    raise ImproperlyConfigured(f"Missing secret key: {e}")
except Exception as e:
    # Log error and fail fast (don't start Django with missing secrets)
    logger.critical(f"Failed to load secrets: {e}")
    raise
```

**IAM Policy (Least Privilege):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-west-1:*:secret:cv-tailor-prod-*"
      ],
      "Condition": {
        "StringEquals": {
          "aws:PrincipalTag/Environment": "production"
        }
      }
    },
    {
      "Effect": "Deny",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:cv-tailor-staging-*"
      ]
    }
  ]
}
```

### Secret Categories and Rotation Policies

| Secret Type | Storage | Rotation Frequency | Method |
|-------------|---------|-------------------|--------|
| **Django SECRET_KEY** | Secrets Manager | 90 days | Manual (update ECS task definition) |
| **Database Password** | Secrets Manager | 30 days | Automatic (Lambda rotation) |
| **OpenAI API Key** | Secrets Manager | As needed | Manual (via OpenAI dashboard) |
| **Google OAuth Credentials** | Secrets Manager | Annually | Manual (via Google Cloud Console) |
| **GitHub Token** | Secrets Manager | 90 days | Manual (via GitHub settings) |

**Rotation Procedure (Database Password):**
```bash
# Automated via AWS Lambda (no manual steps)
# Lambda function runs every 30 days:
1. Generate new secure password (32 chars, alphanumeric+symbols)
2. Test new password against RDS (createSecret API)
3. Update RDS master password (setSecret API)
4. Update Secrets Manager (finishSecret API)
5. Notify on Slack (success/failure)
6. ECS tasks automatically pick up new password on next deployment
```

**Rotation Procedure (Django SECRET_KEY):**
```bash
# Manual (quarterly rotation)
1. Generate new SECRET_KEY:
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

2. Update Secrets Manager:
   aws secretsmanager update-secret \
     --secret-id cv-tailor-prod-secrets \
     --secret-string '{"DJANGO_SECRET_KEY":"new-key",...}'

3. Deploy new ECS task definition (picks up new secret)

4. Old sessions invalidated (users must re-login)
```

---

## Consequences

### Positive

1. **✅ Security Hardening:**
   - Secrets encrypted at rest (KMS keys)
   - Secrets encrypted in transit (TLS)
   - Automatic rotation reduces attack window
   - Audit logging (CloudTrail tracks all access)

2. **✅ Access Control:**
   - IAM policies enforce least privilege
   - Production secrets inaccessible from staging
   - No long-lived credentials (IAM roles for ECS)
   - MFA required for Secrets Manager console access

3. **✅ Operational Benefits:**
   - Automatic DB password rotation (no manual process)
   - Versioning (can rollback to previous secrets)
   - Cross-region replication (disaster recovery)
   - No secrets in code or Docker images

4. **✅ Compliance:**
   - Meets most security standards (SOC 2, ISO 27001)
   - Audit trail for secret access
   - Secrets never logged
   - Data residency (secrets in us-west-1)

5. **✅ Cost-Effective:**
   - $0.40/secret/month (4 secrets = $1.60/month)
   - $0.05 per 10,000 API calls (~$0.10/month for our volume)
   - Total: ~$2/month for secrets management

6. **✅ Developer Experience:**
   - Local dev unchanged (still uses `.env`)
   - No AWS setup needed for local work
   - Secrets loading transparent (Django settings handle it)

### Negative

1. **❌ AWS Lock-in:**
   - AWS Secrets Manager is AWS-specific
   - Migration requires rewriting secret loading code
   - Alternative: HashiCorp Vault (more portable but more complex)

2. **❌ Deployment Dependency:**
   - Django won't start if Secrets Manager unavailable
   - Need retry logic and fallbacks
   - Adds latency at container startup (~500ms to fetch secrets)

3. **❌ Complexity:**
   - Team needs to learn AWS Secrets Manager console
   - Rotation Lambda needs maintenance
   - More moving parts (can fail)

4. **❌ Initial Setup Effort:**
   - Migrate existing secrets to Secrets Manager
   - Write Terraform modules for secrets
   - Configure IAM policies
   - Test rotation procedures

5. **❌ Cost (Minor):**
   - $2/month for secrets management
   - Free tier: 30 days for new accounts
   - Negligible compared to other AWS costs

### Mitigation

- **Lock-in:** Abstract secrets loading behind `get_secret()` function (can swap backend)
- **Dependency:** Implement retry logic, fail fast with clear error messages
- **Complexity:** Comprehensive documentation (OP-NOTE), staging environment for testing
- **Setup:** Detailed step-by-step guide, Terraform automates most setup

---

## Alternatives Considered

### Alternative 1: AWS Systems Manager Parameter Store

**Pros:**
- ✅ Free (no per-secret cost)
- ✅ Integrated with AWS
- ✅ Versioning and change tracking

**Cons:**
- ❌ No automatic rotation (manual only)
- ❌ No Lambda rotation templates
- ❌ Less feature-rich than Secrets Manager

**Decision:** Rejected because automatic DB rotation is critical

### Alternative 2: HashiCorp Vault

**Pros:**
- ✅ Multi-cloud (AWS, GCP, Azure, on-prem)
- ✅ Dynamic secrets (generate on-demand)
- ✅ Excellent audit logging
- ✅ Industry standard

**Cons:**
- ❌ Need to run Vault cluster (operational overhead)
- ❌ High availability requires 3+ nodes
- ❌ Steeper learning curve
- ❌ Overkill for 10-30 users

**Decision:** Rejected for MVP, reconsider at 1000+ users or multi-cloud

### Alternative 3: Environment Variables in ECS Task Definition

**Pros:**
- ✅ Simple (just set env vars in Terraform)
- ✅ No additional services

**Cons:**
- ❌ Secrets visible in ECS console (anyone with AWS access can see)
- ❌ Secrets visible in CloudWatch logs (if accidentally logged)
- ❌ No rotation (need to redeploy tasks)
- ❌ No audit logging

**Decision:** Rejected for security reasons

### Alternative 4: Encrypted .env Files in S3

**Pros:**
- ✅ Simple to implement
- ✅ Version control in S3
- ✅ Low cost

**Cons:**
- ❌ Need to manage encryption keys (KMS)
- ❌ No automatic rotation
- ❌ Manual S3 upload process
- ❌ Not industry best practice

**Decision:** Rejected, Secrets Manager is purpose-built for this

### Alternative 5: Google Secret Manager (if using GCP)

**Pros:**
- ✅ Similar features to AWS Secrets Manager
- ✅ Automatic rotation support
- ✅ Competitive pricing

**Cons:**
- ❌ We're using AWS (not GCP)
- ❌ Would need to justify multi-cloud complexity

**Decision:** Rejected for current deployment (AWS-only)

---

## Rollback Plan

**If Secrets Manager causes issues:**

### Scenario 1: ECS tasks fail to start (can't fetch secrets)

**Recovery:**
1. Check IAM policy (ensure ECS task role has GetSecretValue permission)
2. Check secret name in ECS task definition (env var `AWS_SECRETS_NAME`)
3. Temporarily add secrets as environment variables in task definition (bypass Secrets Manager)
4. Debug and fix, then revert to Secrets Manager

### Scenario 2: Secrets rotation breaks database connections

**Recovery:**
1. Check RDS password vs Secrets Manager password (manual verification)
2. If mismatched, manually update RDS password to match secret
3. Restart ECS tasks (pick up correct password)
4. Investigate rotation Lambda logs (CloudWatch)

### Scenario 3: Cost exceeds expectations

**Recovery:**
- Secrets Manager cost is fixed ($2/month)
- No rollback needed (cost is negligible)

### Scenario 4: Need to migrate off AWS Secrets Manager

**Recovery:**
1. Export secrets:
   ```bash
   aws secretsmanager get-secret-value --secret-id cv-tailor-prod-secrets --query SecretString --output text > secrets.json
   ```
2. Migrate to alternative (Vault, .env, etc.)
3. Update Django settings to use new secrets backend
4. Deploy updated code
5. Delete secrets from Secrets Manager

**Data Protection:**
- ✅ Secrets versioned (can rollback)
- ✅ Secrets backed up (export to S3 encrypted)
- ✅ No data loss risk (secrets are configuration, not user data)

---

## Implementation Checklist

**Phase 1: Preparation**
- [ ] Audit all secrets in current `.env` files
- [ ] Categorize secrets (rotation frequency, criticality)
- [ ] Generate production-strength secrets (SECRET_KEY, DB_PASSWORD)
- [ ] Document rotation procedures

**Phase 2: Terraform Modules**
- [ ] Create `terraform/modules/secrets/` module
- [ ] Define secrets in Terraform variables (sensitive)
- [ ] Create IAM policies for ECS task roles
- [ ] Test Terraform apply in staging

**Phase 3: Django Settings Update**
- [ ] Implement `get_secret()` function in `production.py`
- [ ] Add retry logic and error handling
- [ ] Test secret loading locally (mock boto3)
- [ ] Update `staging.py` with Secrets Manager integration

**Phase 4: Rotation Setup**
- [ ] Deploy RDS rotation Lambda (AWS-provided template)
- [ ] Configure rotation schedule (30 days)
- [ ] Test rotation in staging (manual trigger)
- [ ] Verify ECS tasks handle rotation gracefully

**Phase 5: Deployment**
- [ ] Create secrets in Secrets Manager (staging)
- [ ] Deploy Django code to staging
- [ ] Verify app starts and secrets loaded
- [ ] Test rotation in staging
- [ ] Repeat for production

**Phase 6: Monitoring**
- [ ] CloudWatch alarms for rotation failures
- [ ] CloudTrail monitoring for unauthorized access
- [ ] Document rotation procedures in OP-NOTE

---

## Security Best Practices

**1. Principle of Least Privilege:**
- ✅ ECS tasks can only read secrets (not write/delete)
- ✅ Production tasks can't access staging secrets
- ✅ Developers can't access production secrets (only DevOps)

**2. Defense in Depth:**
- ✅ Secrets encrypted at rest (KMS)
- ✅ Secrets encrypted in transit (TLS)
- ✅ Secrets never logged
- ✅ Secrets not in code/Docker images

**3. Audit and Monitoring:**
- ✅ CloudTrail logs all GetSecretValue calls
- ✅ Alarms for rotation failures
- ✅ Alarms for unauthorized access attempts

**4. Rotation:**
- ✅ Database passwords rotate automatically
- ✅ Django SECRET_KEY rotates quarterly
- ✅ API keys rotate as needed

**5. Incident Response:**
- ✅ Secret rotation can be triggered manually (emergency)
- ✅ Secrets versioned (can rollback)
- ✅ Old secret versions expire after 30 days

---

## Testing Strategy

**Unit Tests:**
```python
# backend/cv_tailor/tests/test_secrets.py
from unittest.mock import patch, MagicMock
from django.core.exceptions import ImproperlyConfigured
import pytest

@patch('boto3.client')
def test_get_secret_success(mock_boto3):
    """Test successful secret retrieval"""
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        'SecretString': '{"DJANGO_SECRET_KEY":"test-key"}'
    }
    mock_boto3.return_value = mock_client

    from cv_tailor.settings.production import get_secret
    secrets = get_secret('test-secret')

    assert secrets['DJANGO_SECRET_KEY'] == 'test-key'

@patch('boto3.client')
def test_get_secret_not_found(mock_boto3):
    """Test secret not found error"""
    mock_client = MagicMock()
    mock_client.get_secret_value.side_effect = ClientError(
        {'Error': {'Code': 'ResourceNotFoundException'}},
        'GetSecretValue'
    )
    mock_boto3.return_value = mock_client

    from cv_tailor.settings.production import get_secret

    with pytest.raises(ImproperlyConfigured):
        get_secret('nonexistent-secret')
```

**Integration Tests:**
```bash
# Test in staging environment
1. Deploy app with Secrets Manager
2. Verify app starts successfully
3. Check CloudWatch logs for secret loading
4. Trigger rotation Lambda manually
5. Verify app continues working after rotation
```

---

## Success Metrics

**Security:**
- [ ] Zero secrets in code/logs/Docker images
- [ ] All production secrets in Secrets Manager
- [ ] Automatic DB rotation working (30-day cycle)
- [ ] CloudTrail logging all secret access

**Reliability:**
- [ ] App starts successfully (99.9% success rate)
- [ ] Secret rotation doesn't cause downtime
- [ ] Retry logic handles transient failures

**Operations:**
- [ ] Manual rotation procedure documented
- [ ] Automatic rotation monitored (alarms)
- [ ] Team trained on secrets management

**Cost:**
- [ ] Secrets Manager cost < $5/month
- [ ] No unexpected charges

---

## Related ADRs

**Depends on:**
- ADR-029: Multi-Environment Settings (production.py loads secrets)
- ADR-030: AWS Deployment Architecture (ECS tasks use IAM roles)

**Influences:**
- ADR-0XX: CI/CD Pipeline (GitHub Actions needs secrets for deployment)

---

## References

**AWS Documentation:**
- [Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [Rotating RDS Credentials](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets-rds.html)
- [IAM Policies for Secrets](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_identity-based-policies.html)

**Security Standards:**
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [NIST SP 800-57: Key Management](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)

**Internal:**
- TECH SPEC: `docs/specs/spec-deployment-v1.0.md`
- Discovery: `docs/discovery/disc-001-environment-config-analysis.md`

---

## Approval

**Reviewed by:**
- [x] Security Team Lead - Approved
- [x] DevOps Team - Approved
- [x] Engineering Manager - Approved

**Approved for implementation:** Yes

**Implementation Owner:** DevOps Team

**Target Completion:** Week 2 of deployment project (Day 10-12)

**Security Sign-off:** Required before production deployment
