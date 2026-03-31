output "alb_dns_name" {
  description = "Public DNS name of the Application Load Balancer — the URL to reach the service."
  value       = module.alb.alb_dns_name
}

output "ecr_repository_url" {
  description = "ECR repository URL used in CI/CD docker push commands."
  value       = module.ecr.repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster."
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS service."
  value       = module.ecs.service_name
}
