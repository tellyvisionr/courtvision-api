output "api_key_arn" {
  description = "ARN of the balldontlie_api_key SSM parameter."
  value       = aws_ssm_parameter.balldontlie_api_key.arn
}

output "base_url_arn" {
  description = "ARN of the balldontlie_base_url SSM parameter."
  value       = aws_ssm_parameter.balldontlie_base_url.arn
}
