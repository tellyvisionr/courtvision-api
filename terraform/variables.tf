variable "aws_region" {
  description = "AWS region to deploy resources into."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short name used as a prefix for all resources."
  type        = string
  default     = "courtvision"
}

variable "environment" {
  description = "Deployment environment (e.g. prod, staging)."
  type        = string
  default     = "prod"
}

variable "container_port" {
  description = "Port the application container listens on."
  type        = number
  default     = 8000
}

variable "desired_count" {
  description = "Number of ECS task replicas to keep running."
  type        = number
  default     = 1
}

variable "task_cpu" {
  description = "Fargate task CPU units (256 = 0.25 vCPU)."
  type        = string
  default     = "256"
}

variable "task_memory" {
  description = "Fargate task memory in MiB."
  type        = string
  default     = "512"
}

variable "health_check_path" {
  description = "HTTP path the ALB target group health check will hit."
  type        = string
  default     = "/health"
}

variable "aws_account_id" {
  description = "AWS account ID. Required for IAM policy ARN construction."
  type        = string
  # TODO: fill in before applying
}

variable "balldontlie_api_key" {
  description = "API key for balldontlie.io — stored in SSM SecureString."
  type        = string
  sensitive   = true
  # TODO: fill in before applying
}
