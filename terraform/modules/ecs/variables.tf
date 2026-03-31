variable "project_name" {
  description = "Project name used as a resource name prefix."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "aws_region" {
  description = "AWS region (used in CloudWatch log configuration)."
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID (used to build SSM parameter ARNs in IAM policy)."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the ECS task security group."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs where Fargate tasks will run."
  type        = list(string)
}

variable "ecr_repository_url" {
  description = "ECR repository URL for the container image."
  type        = string
}

variable "container_port" {
  description = "Port the application container listens on."
  type        = number
}

variable "desired_count" {
  description = "Number of ECS task replicas."
  type        = number
}

variable "task_cpu" {
  description = "Fargate task CPU units."
  type        = string
}

variable "task_memory" {
  description = "Fargate task memory in MiB."
  type        = string
}

variable "alb_security_group_id" {
  description = "Security group ID of the ALB (allows inbound traffic to ECS tasks)."
  type        = string
}

variable "target_group_arn" {
  description = "ARN of the ALB target group to register tasks with."
  type        = string
}

variable "alb_listener_arn" {
  description = "ARN of the ALB HTTP listener (ECS service depends on it)."
  type        = string
}

variable "log_group_name" {
  description = "CloudWatch log group name for container logs."
  type        = string
}

variable "ssm_api_key_arn" {
  description = "ARN of the SSM parameter holding the balldontlie API key."
  type        = string
}

variable "ssm_base_url_arn" {
  description = "ARN of the SSM parameter holding the balldontlie base URL."
  type        = string
}
