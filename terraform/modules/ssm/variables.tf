variable "project_name" {
  description = "Project name used as the SSM parameter path prefix."
  type        = string
}

variable "balldontlie_api_key" {
  description = "API key for balldontlie.io — stored as a SecureString."
  type        = string
  sensitive   = true
}
