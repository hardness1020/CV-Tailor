# Monitoring Module for CV-Tailor
#
# Creates comprehensive monitoring with:
#   - SNS topic for alarm notifications
#   - CloudWatch Dashboard with all key metrics
#   - Composite alarms for system health
#
# Features:
#   - Email notifications for all alarms
#   - Centralized dashboard for all infrastructure
#   - Application, database, cache, and load balancer metrics
#
# Related Documentation:
#   - docs/specs/spec-deployment-v1.0.md

# ============================================================================
# SNS Topic for Alarm Notifications
# ============================================================================

resource "aws_sns_topic" "alarms" {
  name = "${var.project_name}-${var.environment}-alarms"

  tags = {
    Name = "${var.project_name}-${var.environment}-alarms"
  }
}

# SNS Topic Subscription (Email)
resource "aws_sns_topic_subscription" "alarm_email" {
  count = var.alarm_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# ============================================================================
# CloudWatch Dashboard
# ============================================================================

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-${var.environment}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # ========================================================================
      # ALB Metrics
      # ========================================================================
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", { stat = "Average", label = "Avg Response Time" }],
            [".", ".", { stat = "p99", label = "p99 Response Time" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ALB - Response Time"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", { stat = "Sum", label = "Total Requests" }],
            [".", "HTTPCode_Target_2XX_Count", { stat = "Sum", label = "2xx Responses" }],
            [".", "HTTPCode_Target_4XX_Count", { stat = "Sum", label = "4xx Responses" }],
            [".", "HTTPCode_Target_5XX_Count", { stat = "Sum", label = "5xx Responses" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ALB - Request Count & HTTP Codes"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "HealthyHostCount", { stat = "Average", label = "Healthy Targets" }],
            [".", "UnHealthyHostCount", { stat = "Average", label = "Unhealthy Targets" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ALB - Target Health"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },

      # ========================================================================
      # ECS Metrics
      # ========================================================================
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", { stat = "Average", label = "CPU Utilization" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ECS - CPU Utilization"
          period  = 300
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ECS", "MemoryUtilization", { stat = "Average", label = "Memory Utilization" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ECS - Memory Utilization"
          period  = 300
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["ECS/ContainerInsights", "RunningTaskCount", { stat = "Average", label = "Running Tasks" }],
            [".", "DesiredTaskCount", { stat = "Average", label = "Desired Tasks" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ECS - Task Count"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },

      # ========================================================================
      # RDS Metrics
      # ========================================================================
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", { stat = "Average", label = "CPU Utilization" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "RDS - CPU Utilization"
          period  = 300
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "DatabaseConnections", { stat = "Average", label = "Active Connections" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "RDS - Database Connections"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "FreeStorageSpace", { stat = "Average", label = "Free Storage" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "RDS - Free Storage Space"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "ReadLatency", { stat = "Average", label = "Read Latency" }],
            [".", "WriteLatency", { stat = "Average", label = "Write Latency" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "RDS - I/O Latency"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },

      # ========================================================================
      # ElastiCache Metrics
      # ========================================================================
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ElastiCache", "CPUUtilization", { stat = "Average", label = "CPU Utilization" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ElastiCache - CPU Utilization"
          period  = 300
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ElastiCache", "DatabaseMemoryUsagePercentage", { stat = "Average", label = "Memory Usage" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ElastiCache - Memory Usage"
          period  = 300
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ElastiCache", "CacheHits", { stat = "Sum", label = "Cache Hits" }],
            [".", "CacheMisses", { stat = "Sum", label = "Cache Misses" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ElastiCache - Cache Hit/Miss"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ElastiCache", "Evictions", { stat = "Sum", label = "Evictions" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ElastiCache - Evictions"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      }
    ]
  })
}

# ============================================================================
# Composite Alarm for Overall System Health
# ============================================================================

resource "aws_cloudwatch_composite_alarm" "system_health" {
  count = var.enable_composite_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-system-unhealthy"
  alarm_description   = "Composite alarm indicating overall system health issues"
  actions_enabled     = true
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  insufficient_data_actions = []

  # Trigger if ANY of the critical alarms are in ALARM state
  alarm_rule = length(var.critical_alarm_names) > 0 ? join(" OR ", var.critical_alarm_names) : "ALARM(${aws_sns_topic.alarms.name})"

  tags = {
    Name = "${var.project_name}-${var.environment}-system-health"
  }

  depends_on = [aws_sns_topic.alarms]
}

# ============================================================================
# CloudWatch Log Metric Filters (Application Errors)
# ============================================================================

# Filter for ERROR log messages
resource "aws_cloudwatch_log_metric_filter" "application_errors" {
  count = var.ecs_log_group_name != "" ? 1 : 0

  name           = "${var.project_name}-${var.environment}-application-errors"
  log_group_name = var.ecs_log_group_name
  pattern        = "[time, request_id, level = ERROR*, ...]"

  metric_transformation {
    name      = "ApplicationErrors"
    namespace = "${var.project_name}/${var.environment}"
    value     = "1"
    unit      = "Count"
  }
}

# Alarm for application errors
resource "aws_cloudwatch_metric_alarm" "application_errors" {
  count = var.ecs_log_group_name != "" ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-application-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApplicationErrors"
  namespace           = "${var.project_name}/${var.environment}"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Application is logging too many ERROR messages"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name = "${var.project_name}-${var.environment}-app-errors-alarm"
  }
}
