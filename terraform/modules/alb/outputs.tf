output "alb_dns_name" {
  description = "Public DNS name of the Application Load Balancer."
  value       = aws_lb.main.dns_name
}

output "alb_arn_suffix" {
  description = "ARN suffix of the ALB (used in CloudWatch metric dimensions)."
  value       = aws_lb.main.arn_suffix
}

output "alb_security_group_id" {
  description = "Security group ID of the ALB (referenced by ECS task security group)."
  value       = aws_security_group.alb.id
}

output "target_group_arn" {
  description = "ARN of the ALB target group."
  value       = aws_lb_target_group.main.arn
}

output "http_listener_arn" {
  description = "ARN of the HTTP listener (ECS service depends on this)."
  value       = aws_lb_listener.http.arn
}
