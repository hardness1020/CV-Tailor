# S3 Module for CV-Tailor
#
# Creates S3 buckets for:
#   - Media files (user uploads, generated documents)
#   - Static files (CSS, JS, images)
#
# Features:
#   - Encryption at rest
#   - Versioning
#   - Lifecycle policies
#   - CORS configuration
#   - CloudWatch metrics
#
# Related Documentation:
#   - docs/specs/spec-deployment-v1.0.md

# ============================================================================
# Media Bucket (User Uploads, Generated Documents)
# ============================================================================

resource "aws_s3_bucket" "media" {
  bucket = var.media_bucket_name != "" ? var.media_bucket_name : "${var.project_name}-${var.environment}-media"

  tags = {
    Name    = "${var.project_name}-${var.environment}-media"
    Type    = "media"
    Purpose = "User uploads and generated documents"
  }
}

# Enable versioning for media bucket
resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption for media bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Block public access for media bucket
resource "aws_s3_bucket_public_access_block" "media" {
  bucket = aws_s3_bucket.media.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS configuration for media bucket
resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE"]
    allowed_origins = var.allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Lifecycle policy for media bucket
resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  # Delete old versions after 90 days
  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  # Move old documents to Glacier after 180 days
  rule {
    id     = "archive-old-documents"
    status = "Enabled"

    filter {
      prefix = "documents/"
    }

    transition {
      days          = 180
      storage_class = "GLACIER"
    }
  }

  # Delete incomplete multipart uploads after 7 days
  rule {
    id     = "cleanup-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ============================================================================
# Static Files Bucket (CSS, JS, Images)
# ============================================================================

resource "aws_s3_bucket" "static" {
  bucket = var.static_bucket_name != "" ? var.static_bucket_name : "${var.project_name}-${var.environment}-static"

  tags = {
    Name    = "${var.project_name}-${var.environment}-static"
    Type    = "static"
    Purpose = "Static assets - CSS JS images"
  }
}

# Enable versioning for static bucket
resource "aws_s3_bucket_versioning" "static" {
  bucket = aws_s3_bucket.static.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption for static bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "static" {
  bucket = aws_s3_bucket.static.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Public access settings for static bucket (allow public read)
resource "aws_s3_bucket_public_access_block" "static" {
  bucket = aws_s3_bucket.static.id

  block_public_acls       = true
  block_public_policy     = false  # Allow bucket policy for public read
  ignore_public_acls      = true
  restrict_public_buckets = false  # Allow public read via policy
}

# Bucket policy for public read access to static files
resource "aws_s3_bucket_policy" "static" {
  bucket = aws_s3_bucket.static.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.static.arn}/*"
      }
    ]
  })
}

# CORS configuration for static bucket
resource "aws_s3_bucket_cors_configuration" "static" {
  bucket = aws_s3_bucket.static.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET"]
    allowed_origins = var.allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

# Lifecycle policy for static bucket
resource "aws_s3_bucket_lifecycle_configuration" "static" {
  bucket = aws_s3_bucket.static.id

  # Delete old versions after 30 days
  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  # Delete incomplete multipart uploads after 3 days
  rule {
    id     = "cleanup-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 3
    }
  }
}

# ============================================================================
# CloudWatch Alarms for S3
# ============================================================================

# Media bucket size alarm (warning when > 100 GB)
resource "aws_cloudwatch_metric_alarm" "media_bucket_size" {
  count = var.enable_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-media-bucket-size"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "BucketSizeBytes"
  namespace           = "AWS/S3"
  period              = "86400"  # 24 hours
  statistic           = "Average"
  threshold           = "107374182400"  # 100 GB in bytes
  alarm_description   = "Media bucket size exceeds 100 GB"
  alarm_actions       = var.alarm_actions
  treat_missing_data  = "notBreaching"

  dimensions = {
    BucketName  = aws_s3_bucket.media.id
    StorageType = "StandardStorage"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-media-bucket-size-alarm"
  }
}

# Static bucket size alarm (warning when > 10 GB)
resource "aws_cloudwatch_metric_alarm" "static_bucket_size" {
  count = var.enable_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-static-bucket-size"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "BucketSizeBytes"
  namespace           = "AWS/S3"
  period              = "86400"  # 24 hours
  statistic           = "Average"
  threshold           = "10737418240"  # 10 GB in bytes
  alarm_description   = "Static bucket size exceeds 10 GB"
  alarm_actions       = var.alarm_actions
  treat_missing_data  = "notBreaching"

  dimensions = {
    BucketName  = aws_s3_bucket.static.id
    StorageType = "StandardStorage"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-static-bucket-size-alarm"
  }
}
