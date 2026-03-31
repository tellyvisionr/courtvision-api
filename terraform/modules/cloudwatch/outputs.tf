output "log_group_name" {
  description = "Name of the CloudWatch log group for ECS container logs."
  value       = aws_cloudwatch_log_group.ecs.name
}

output "log_group_arn" {
  description = "ARN of the CloudWatch log group."
  value       = aws_cloudwatch_log_group.ecs.arn
}
