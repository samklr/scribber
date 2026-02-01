# =============================================================================
# Terraform Variables
# =============================================================================

variable "project_id" {
  description = "Cloud project ID"
  type        = string
}

variable "project_name" {
  description = "Human-readable project name"
  type        = string
  default     = "Project Template"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "region" {
  description = "Primary region for resources"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

# Database
variable "db_tier" {
  description = "Database instance tier/size"
  type        = string
  default     = "db-f1-micro" # GCP / db.t3.micro for AWS
}

variable "db_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "POSTGRES_16"
}

# Container resources
variable "backend_cpu" {
  description = "CPU allocation for backend"
  type        = string
  default     = "1"
}

variable "backend_memory" {
  description = "Memory allocation for backend"
  type        = string
  default     = "512Mi"
}

variable "frontend_cpu" {
  description = "CPU allocation for frontend"
  type        = string
  default     = "1"
}

variable "frontend_memory" {
  description = "Memory allocation for frontend"
  type        = string
  default     = "256Mi"
}
