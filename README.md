# 🏀 CourtVision API

CourtVision is a **basketball statistics microservice** designed to showcase end-to-end DevOps and Platform Engineering skills — combining modern infrastructure, automation, and cloud deployment practices.

Built with **FastAPI**, containerized with **Docker**, provisioned with **Terraform**, and deployed to **AWS ECS (Fargate)** via a **GitHub Actions CI/CD pipeline**, this project demonstrates how to build, ship, and operate production-ready cloud services.

---

## 🚀 Key Features
- **FastAPI backend** serving live NBA data from the [balldontlie.io](https://www.balldontlie.io) API
- **Containerized** application (Docker) for consistent environment parity
- **Automated CI/CD pipeline** using GitHub Actions to test, build, and deploy on every push
- **Infrastructure as Code (IaC)** using Terraform to provision ECS, ALB, and networking
- **Cloud-native deployment** on AWS Fargate (serverless containers)
- **Health checks & observability** via ALB target group monitoring and CloudWatch logs

---

## ⚙️ Tech Stack
| Layer | Tools |
|-------|-------|
| **Backend** | Python, FastAPI, Pydantic |
| **Infrastructure** | Terraform, AWS ECS/Fargate, ALB, ECR |
| **CI/CD** | GitHub Actions |
| **Containerization** | Docker |
| **Monitoring** | AWS CloudWatch (logs & health checks) |

---

## 🧠 Example Endpoints
| Route | Description |
|--------|-------------|
| `/health` | Service heartbeat |
| `/player/{name}` | Returns season averages for a player |
| `/team/{name}` | Returns team info |
| `/compare?player1=kobe&player2=lebron` | Compares two players’ stats |

---

## 🧩 Architecture Overview
Developer Push → GitHub Actions → Terraform → AWS ECS (Fargate) → Application Load Balancer → FastAPI Service
