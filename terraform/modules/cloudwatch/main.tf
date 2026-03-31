resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 14

  tags = {
    Project = var.project_name
  }
}

# Alert when average CPU across the ECS service exceeds 80% for 10 minutes.
resource "aws_cloudwatch_metric_alarm" "ecs_high_cpu" {
  alarm_name          = "${var.project_name}-high-cpu"
  alarm_description   = "ECS service CPU utilization is above 80% for 10 minutes."
  namespace           = "AWS/ECS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }
}

# Alert when the ALB returns 10+ 5xx responses in a single 60-second window.
resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "${var.project_name}-alb-5xx"
  alarm_description   = "ALB is returning elevated 5xx error responses."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 10
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }
}
