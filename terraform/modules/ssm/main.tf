# ---------------------------------------------------------------------------
# SSM Parameter Store — runtime secrets injected into ECS tasks at launch.
# The API key is stored as SecureString (KMS-encrypted with the AWS-managed
# key). The base URL is non-sensitive and stored as a plain String.
# ---------------------------------------------------------------------------

resource "aws_ssm_parameter" "balldontlie_api_key" {
  name        = "/${var.project_name}/balldontlie_api_key"
  description = "balldontlie.io API key for the CourtVision service."
  type        = "SecureString"
  value       = var.balldontlie_api_key

  tags = {
    Project = var.project_name
  }
}

resource "aws_ssm_parameter" "balldontlie_base_url" {
  name        = "/${var.project_name}/balldontlie_base_url"
  description = "balldontlie.io base URL for the CourtVision service."
  type        = "String"
  value       = "https://api.balldontlie.io/v1"

  tags = {
    Project = var.project_name
  }
}
