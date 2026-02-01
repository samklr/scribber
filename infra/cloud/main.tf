# =============================================================================
# Terraform Configuration - Cloud Infrastructure
# =============================================================================
# This is a placeholder for cloud infrastructure.
# Customize based on your cloud provider (GCP, AWS, Azure).
# =============================================================================

terraform {
  required_version = ">= 1.0"

  # Configure your backend for state storage
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "project-template"
  # }

  required_providers {
    # Google Cloud Platform
    # google = {
    #   source  = "hashicorp/google"
    #   version = "~> 5.0"
    # }

    # AWS
    # aws = {
    #   source  = "hashicorp/aws"
    #   version = "~> 5.0"
    # }
  }
}

# =============================================================================
# Variables
# =============================================================================

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "project-template"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "region" {
  description = "Cloud region"
  type        = string
  default     = "us-central1" # or eu-west-1 for AWS
}

# =============================================================================
# Outputs
# =============================================================================

output "info" {
  value = <<-EOT

    Cloud Infrastructure Placeholder
    =================================

    This Terraform configuration is a starting point.
    Customize it based on your cloud provider:

    GCP (Google Cloud Platform):
    - Cloud Run for containers
    - Cloud SQL for PostgreSQL
    - Cloud Storage for assets
    - Cloud Build for CI/CD

    AWS:
    - ECS/Fargate for containers
    - RDS for PostgreSQL
    - S3 for assets
    - CodePipeline for CI/CD

    Azure:
    - Container Apps for containers
    - Azure Database for PostgreSQL
    - Blob Storage for assets
    - Azure DevOps for CI/CD

  EOT
}
