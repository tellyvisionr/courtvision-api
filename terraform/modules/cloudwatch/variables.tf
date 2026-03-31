variable "project_name" {
  description = "Project name used as a resource name prefix."
  type        = string
}

variable "alb_arn_suffix" {
  description = "The ARN suffix of the ALB (used in CloudWatch metric dimensions)."
  type        = string
}

variable "ecs_cluster_name" {
  description = "Name of the ECS cluster (used in CloudWatch metric dimensions)."
  type        = string
}

variable "ecs_service_name" {
  description = "Name of the ECS service (used in CloudWatch metric dimensions)."
  type        = string
}
