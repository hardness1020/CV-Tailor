# CloudFront Security Headers Configuration Guide

**Purpose**: Configure security headers and Content Security Policy for CV-Tailor frontend via AWS CloudFront

**Last Updated**: October 24, 2025
**CloudFront Distribution**: <CLOUDFRONT_DISTRIBUTION_ID>
**Status**: 🔧 Pending Implementation

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Response Headers Policy](#response-headers-policy)
4. [Content Security Policy](#content-security-policy)
5. [Implementation Steps](#implementation-steps)
6. [Testing & Validation](#testing--validation)
7. [Rollback Plan](#rollback-plan)
8. [Monitoring](#monitoring)

---

## Overview

Security headers protect against common web vulnerabilities including:
- **XSS** (Cross-Site Scripting)
- **Clickjacking**
- **MIME-type sniffing**
- **Information leakage**
- **Feature abuse** (camera, microphone access)

These headers are added via **CloudFront Response Headers Policy** to avoid modifying application code.

---

## Prerequisites

- **AWS CLI** installed and configured (`aws configure`)
- **CloudFront Distribution ID**: `<CLOUDFRONT_DISTRIBUTION_ID>`
- **AWS Region**: `us-east-1` (CloudFront is global, but config commands use us-east-1)
- **Permissions**: `cloudfront:CreateResponseHeadersPolicy`, `cloudfront:UpdateDistribution`

---

## Response Headers Policy

### Step 1: Create Response Headers Policy

Create a file named `security-headers-policy.json`:

```json
{
  "ResponseHeadersPolicyConfig": {
    "Name": "cv-tailor-security-headers",
    "Comment": "Security headers for CV-Tailor frontend",
    "SecurityHeadersConfig": {
      "StrictTransportSecurity": {
        "AccessControlMaxAgeSec": 31536000,
        "IncludeSubdomains": true,
        "Preload": false,
        "Override": true
      },
      "XSSProtection": {
        "ModeBlock": true,
        "Protection": true,
        "Override": true
      },
      "FrameOptions": {
        "FrameOption": "DENY",
        "Override": true
      },
      "ContentTypeOptions": {
        "Override": true
      },
      "ReferrerPolicy": {
        "ReferrerPolicy": "strict-origin-when-cross-origin",
        "Override": true
      }
    },
    "CustomHeadersConfig": {
      "Items": [
        {
          "Header": "Permissions-Policy",
          "Value": "camera=(), microphone=(), geolocation=()",
          "Override": true
        }
      ]
    }
  }
}
```

### Step 2: Create the Policy via AWS CLI

```bash
aws cloudfront create-response-headers-policy \
  --response-headers-policy-config file://security-headers-policy.json \
  --region us-east-1
```

**Expected Output**:
```json
{
  "ResponseHeadersPolicy": {
    "Id": "ABCD1234EFGH5678",
    "LastModifiedTime": "2025-10-24T...",
    ...
  }
}
```

**Save the Policy ID** (e.g., `ABCD1234EFGH5678`) - you'll need it in the next step.

---

## Content Security Policy

### Why CSP?

Content Security Policy is the **strongest defense** against XSS attacks. It tells browsers:
- Which scripts are allowed to run
- Where resources can be loaded from
- What inline styles are permitted

### CSP Configuration

Create `csp-policy.json`:

```json
{
  "ResponseHeadersPolicyConfig": {
    "Name": "cv-tailor-csp-policy",
    "Comment": "Content Security Policy for CV-Tailor",
    "CustomHeadersConfig": {
      "Items": [
        {
          "Header": "Content-Security-Policy",
          "Value": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://api.<YOUR_DOMAIN>; font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none';",
          "Override": true
        }
      ]
    }
  }
}
```

### CSP Directives Explained

| Directive | Value | Purpose |
|-----------|-------|---------|
| `default-src 'self'` | Same origin only | Default policy for all resource types |
| `script-src 'self'` | Same origin scripts only | **Blocks inline scripts** - strongest XSS protection |
| `style-src 'self' 'unsafe-inline'` | Allows inline styles | Required for Tailwind CSS |
| `img-src 'self' data: https:` | Self, data URIs, HTTPS images | Allows image loading |
| `connect-src` | Self + API domain | Restricts AJAX/fetch to backend only |
| `font-src 'self'` | Self-hosted fonts only | Restricts font loading |
| `object-src 'none'` | No plugins | Blocks Flash, Java applets |
| `frame-ancestors 'none'` | No embedding | Prevents clickjacking |

### Testing CSP (Recommended: Report-Only Mode First)

For initial testing, use `Content-Security-Policy-Report-Only`:

```json
{
  "Header": "Content-Security-Policy-Report-Only",
  "Value": "default-src 'self'; ...; report-uri /csp-report-endpoint",
  "Override": true
}
```

This reports violations without blocking them. Monitor for 1-2 weeks before switching to enforcing mode.

---

## Implementation Steps

### Option A: AWS Console (Recommended for First Time)

1. **Navigate to CloudFront**:
   - Go to AWS Console → CloudFront → Distributions
   - Click on distribution `<CLOUDFRONT_DISTRIBUTION_ID>`

2. **Create Response Headers Policy**:
   - Go to **Policies** → **Response headers** → **Create policy**
   - Name: `cv-tailor-security-headers`
   - Configure headers as shown in JSON above
   - Click **Create**

3. **Create CSP Policy**:
   - Repeat step 2 for CSP policy
   - Name: `cv-tailor-csp-policy`

4. **Attach to Distribution**:
   - Go back to your distribution → **Behaviors** tab
   - Edit the default behavior (`*`)
   - **Response headers policy**: Select `cv-tailor-security-headers`
   - OR select `cv-tailor-csp-policy` (choose one based on testing)
   - Click **Save changes**

5. **Wait for Deployment** (5-15 minutes):
   - Status will change from "In Progress" to "Deployed"

### Option B: AWS CLI (Automated)

```bash
#!/bin/bash
# deploy-security-headers.sh

# 1. Create security headers policy
SECURITY_POLICY_ID=$(aws cloudfront create-response-headers-policy \
  --response-headers-policy-config file://security-headers-policy.json \
  --region us-east-1 \
  --query 'ResponseHeadersPolicy.Id' \
  --output text)

echo "Security Headers Policy ID: $SECURITY_POLICY_ID"

# 2. Get current distribution config
aws cloudfront get-distribution-config \
  --id <CLOUDFRONT_DISTRIBUTION_ID> \
  --region us-east-1 > current-config.json

# Extract ETag (required for updates)
ETAG=$(jq -r '.ETag' current-config.json)

# 3. Update distribution config JSON to include policy ID
jq ".DistributionConfig.DefaultCacheBehavior.ResponseHeadersPolicyId = \"$SECURITY_POLICY_ID\"" \
  current-config.json > updated-config.json

# 4. Update CloudFront distribution
aws cloudfront update-distribution \
  --id <CLOUDFRONT_DISTRIBUTION_ID> \
  --distribution-config file://updated-config.json \
  --if-match "$ETAG" \
  --region us-east-1

echo "CloudFront distribution updated. Deployment in progress (5-15 minutes)..."
```

### Option C: Terraform (Infrastructure as Code)

```hcl
# terraform/cloudfront-security.tf

resource "aws_cloudfront_response_headers_policy" "security_headers" {
  name    = "cv-tailor-security-headers"
  comment = "Security headers for CV-Tailor frontend"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      preload                    = false
      override                   = true
    }

    xss_protection {
      mode_block = true
      protection = true
      override   = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    content_type_options {
      override = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
  }

  custom_headers_config {
    items {
      header   = "Permissions-Policy"
      value    = "camera=(), microphone=(), geolocation=()"
      override = true
    }
  }
}

resource "aws_cloudfront_distribution" "frontend" {
  # ... existing configuration ...

  default_cache_behavior {
    # ... existing settings ...
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security_headers.id
  }
}
```

Apply with:
```bash
cd terraform/production
terraform plan
terraform apply
```

---

## Testing & Validation

### Step 1: Wait for Deployment

```bash
aws cloudfront get-distribution \
  --id <CLOUDFRONT_DISTRIBUTION_ID> \
  --region us-east-1 \
  --query 'Distribution.Status'
```

Wait until status is `"Deployed"`.

### Step 2: Test Security Headers

```bash
# Test from command line
curl -I https://<YOUR_DOMAIN> | grep -E "(X-|Content-Security|Strict-Transport|Permissions)"

# Expected output:
# strict-transport-security: max-age=31536000; includeSubDomains
# x-frame-options: DENY
# x-content-type-options: nosniff
# x-xss-protection: 1; mode=block
# referrer-policy: strict-origin-when-cross-origin
# permissions-policy: camera=(), microphone=(), geolocation=()
```

### Step 3: Browser DevTools Testing

1. Open https://<YOUR_DOMAIN> in Chrome
2. Open DevTools (F12) → **Network** tab
3. Refresh page
4. Click on the first request (document)
5. Go to **Headers** tab → **Response Headers**
6. Verify all security headers are present

### Step 4: CSP Validator

Use online tools:
- **Mozilla CSP Evaluator**: https://observatory.mozilla.org/
- **CSP Validator**: https://cspvalidator.org/

Enter `https://<YOUR_DOMAIN>` and check for CSP grade.

### Step 5: Security Headers Check

Use:
- **SecurityHeaders.com**: https://securityheaders.com/?q=https://<YOUR_DOMAIN>
- **Mozilla Observatory**: https://observatory.mozilla.org/analyze/<YOUR_DOMAIN>

**Target Grade**: A+ (with all headers implemented)

---

## Rollback Plan

### If Issues Occur

**Option 1: Remove Policy from Distribution** (Fastest)

```bash
# 1. Get current config
aws cloudfront get-distribution-config \
  --id <CLOUDFRONT_DISTRIBUTION_ID> \
  --region us-east-1 > rollback-config.json

# 2. Extract ETag
ETAG=$(jq -r '.ETag' rollback-config.json)

# 3. Remove policy ID
jq 'del(.DistributionConfig.DefaultCacheBehavior.ResponseHeadersPolicyId)' \
  rollback-config.json > rollback-updated.json

# 4. Update distribution
aws cloudfront update-distribution \
  --id <CLOUDFRONT_DISTRIBUTION_ID> \
  --distribution-config file://rollback-updated.json \
  --if-match "$ETAG" \
  --region us-east-1
```

**Option 2: Delete Policy** (After removal from distribution)

```bash
aws cloudfront delete-response-headers-policy \
  --id <POLICY_ID> \
  --if-match <ETAG> \
  --region us-east-1
```

---

## Monitoring

### CloudFront Metrics

Monitor in CloudWatch:
- **4xx Error Rate**: CSP blocking resources?
- **5xx Error Rate**: Server errors?
- **Cache Hit Rate**: Still good after changes?

### CSP Violation Reports

If using `report-uri` directive:
1. Create Lambda function to receive reports
2. Store in CloudWatch Logs or S3
3. Analyze violations weekly

Example Lambda:
```python
import json

def lambda_handler(event, context):
    csp_report = json.loads(event['body'])
    print(json.dumps(csp_report, indent=2))
    return {'statusCode': 204}
```

---

## FAQ

**Q: Will CSP break my application?**
A: Test with `Content-Security-Policy-Report-Only` first. Monitor for violations.

**Q: Why allow 'unsafe-inline' for styles?**
A: Tailwind CSS uses inline styles. Future: Consider nonce-based CSP.

**Q: How often should I update the CSP?**
A: Review quarterly or when adding new external services.

**Q: Can I test locally?**
A: Yes, add meta tag in `index.html`:
```html
<meta http-equiv="Content-Security-Policy" content="...">
```

**Q: What if CloudFront is slow to update?**
A: Invalidate cache:
```bash
aws cloudfront create-invalidation \
  --distribution-id <CLOUDFRONT_DISTRIBUTION_ID> \
  --paths "/*"
```

---

## Next Steps

1. ✅ Review this guide
2. 🔧 Test CSP in **report-only mode** (1-2 weeks)
3. 🔧 Switch to **enforcing mode**
4. 🔧 Monitor CloudWatch metrics
5. 🔧 Run security scan (SecurityHeaders.com)
6. 🔧 Document results in `frontend-security.md`

---

## References

- **CloudFront Response Headers**: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/adding-response-headers.html
- **CSP Specification**: https://www.w3.org/TR/CSP3/
- **CSP Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html
- **Security Headers Guide**: https://securityheaders.com/

---

**Document Version**: 1.0
**Author**: Engineering Team
**Review Date**: Q1 2026
