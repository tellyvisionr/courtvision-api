terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.40"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ---------------------------------------------------------------------------
# VPC — public subnets only (no NAT Gateway; cost-saving for personal project)
# ---------------------------------------------------------------------------
module "vpc" {
  source = "./modules/vpc"

  project_name = var.project_name
  environment  = var.environment
}

# ---------------------------------------------------------------------------
# ECR — container image registry
# ---------------------------------------------------------------------------
module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment
}

# ---------------------------------------------------------------------------
# SSM — parameter store for runtime secrets
# ---------------------------------------------------------------------------
module "ssm" {
  source = "./modules/ssm"

  project_name         = var.project_name
  balldontlie_api_key  = var.balldontlie_api_key
}

# ---------------------------------------------------------------------------
# CloudWatch — log group + metric alarms
# ---------------------------------------------------------------------------
module "cloudwatch" {
  source = "./modules/cloudwatch"

  project_name      = var.project_name
  alb_arn_suffix    = module.alb.alb_arn_suffix
  ecs_cluster_name  = "${var.project_name}-cluster"
  ecs_service_name  = "${var.project_name}-service"
}

# ---------------------------------------------------------------------------
# ALB — public-facing Application Load Balancer
# ---------------------------------------------------------------------------
module "alb" {
  source = "./modules/alb"

  project_name      = var.project_name
  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  container_port    = var.container_port
  health_check_path = var.health_check_path
}

# ---------------------------------------------------------------------------
# ECS — Fargate cluster, task definition, and service
# ---------------------------------------------------------------------------
module "ecs" {
  source = "./modules/ecs"

  project_name               = var.project_name
  environment                = var.environment
  aws_region                 = var.aws_region
  aws_account_id             = var.aws_account_id
  vpc_id                     = module.vpc.vpc_id
  public_subnet_ids          = module.vpc.public_subnet_ids
  ecr_repository_url         = module.ecr.repository_url
  container_port             = var.container_port
  desired_count              = var.desired_count
  task_cpu                   = var.task_cpu
  task_memory                = var.task_memory
  alb_security_group_id      = module.alb.alb_security_group_id
  target_group_arn           = module.alb.target_group_arn
  alb_listener_arn           = module.alb.http_listener_arn
  log_group_name             = module.cloudwatch.log_group_name
  ssm_api_key_arn            = module.ssm.api_key_arn
  ssm_base_url_arn           = module.ssm.base_url_arn
}
