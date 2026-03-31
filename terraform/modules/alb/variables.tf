variable "project_name" {
  description = "Project name used as a resource name prefix."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC to place the ALB in."
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs for the ALB."
  type        = list(string)
}

variable "container_port" {
  description = "Port the application container listens on (target group port)."
  type        = number
}

variable "health_check_path" {
  description = "HTTP path for the target group health check."
  type        = string
}
