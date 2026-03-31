# ---------------------------------------------------------------------------
# ECS Cluster
# ---------------------------------------------------------------------------
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  tags = {
    Name        = "${var.project_name}-cluster"
    Project     = var.project_name
    Environment = var.environment
  }
}

# ---------------------------------------------------------------------------
# IAM — Task Execution Role
# Allows ECS to pull images from ECR, write logs to CloudWatch, and read
# secrets from SSM Parameter Store.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "task_execution" {
  name               = "${var.project_name}-ecs-task-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "task_execution_managed" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Inline policy granting read access to the specific SSM parameters.
resource "aws_iam_role_policy" "task_execution_ssm" {
  name = "${var.project_name}-ssm-read"
  role = aws_iam_role.task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameters"]
        Resource = [
          var.ssm_api_key_arn,
          var.ssm_base_url_arn,
        ]
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# IAM — Task Role
# The role assumed by the running container. Empty for now; extend as needed
# (e.g. S3 read, DynamoDB access).
# ---------------------------------------------------------------------------
resource "aws_iam_role" "task" {
  name               = "${var.project_name}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# ---------------------------------------------------------------------------
# ECS Task Definition
# ---------------------------------------------------------------------------
resource "aws_ecs_task_definition" "main" {
  family                   = "${var.project_name}-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name  = "app"
      image = "${var.ecr_repository_url}:latest"

      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]

      # Pull runtime secrets from SSM at task launch time.
      secrets = [
        {
          name      = "BALLDONTLIE_API_KEY"
          valueFrom = var.ssm_api_key_arn
        },
        {
          name      = "BALLDONTLIE_BASE_URL"
          valueFrom = var.ssm_base_url_arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = var.log_group_name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      essential = true
    }
  ])

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# ---------------------------------------------------------------------------
# Security Group — ECS Tasks
# Only accept traffic on the container port from the ALB security group.
# Unrestricted outbound is required for ECR image pulls, SSM, and CloudWatch.
# ---------------------------------------------------------------------------
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Allow inbound from ALB only; allow all outbound for AWS service calls."
  vpc_id      = var.vpc_id

  ingress {
    description     = "App traffic from ALB"
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [var.alb_security_group_id]
  }

  egress {
    description = "Allow all outbound (ECR, SSM, CloudWatch)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-ecs-tasks-sg"
    Project     = var.project_name
    Environment = var.environment
  }
}

# ---------------------------------------------------------------------------
# ECS Service
# ---------------------------------------------------------------------------
resource "aws_ecs_service" "main" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.main.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    # Tasks need a public IP to reach ECR, SSM, and CloudWatch without
    # a NAT Gateway (cost-saving trade-off for a personal/dev project).
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "app"
    container_port   = var.container_port
  }

  # Ensure the ALB listener exists before the service tries to register targets.
  depends_on = [var.alb_listener_arn]

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}
