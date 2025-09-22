# variables.tf - Variable definitions for USAJobs ETL infrastructure

# GCP Configuration
variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
  # Replace with your actual project ID
  default     = "ingestion-poc-472904"
}

variable "gcp_region" {
  description = "GCP region for deployment"
  type        = string
  default     = "europe-west2"
}

# Docker Configuration
variable "docker_image" {
  description = "Docker image for the ETL job"
  type        = string
  # Update with your Artifact Registry image
  default     = "europe-west2-docker.pkg.dev/ingestion-poc-472904/usajobs-etl-repo/usajobs-etl:amd64"
}

# Database Configuration (Supabase/Neon/Cloud SQL)
variable "database_url" {
  description = "PostgreSQL connection string (should use Secret Manager in production)"
  type        = string
  sensitive   = true
  # Example: postgresql://user:password@host:5432/dbname
  # For Supabase: postgresql://postgres:[password]@db.xxxx.supabase.co:5432/postgres
  # For Neon: postgresql://user:password@xxx.neon.tech:5432/dbname
}

# API Configuration
variable "usajobs_api_key" {
  description = "USAJobs API key (should use Secret Manager in production)"
  type        = string
  sensitive   = true
}

# ETL Configuration
variable "default_location" {
  description = "Default location for job search"
  type        = string
  default     = "Chicago"
}

variable "keyword" {
  description = "Search keyword for jobs"
  type        = string
  default     = "data engineering"
}

variable "log_level" {
  description = "Logging level for the application"
  type        = string
  default     = "INFO"
  
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
  }
}

# Performance Configuration
variable "max_pages" {
  description = "Maximum number of API pages to fetch"
  type        = number
  default     = 10
}

variable "batch_commit_size" {
  description = "Number of records to commit in each batch"
  type        = number
  default     = 100
}

variable "enable_parallel" {
  description = "Enable parallel processing"
  type        = string
  default     = "false"
  
  validation {
    condition     = contains(["true", "false"], var.enable_parallel)
    error_message = "Must be either 'true' or 'false'"
  }
}

variable "max_workers" {
  description = "Number of parallel workers if enabled"
  type        = number
  default     = 1
  
  validation {
    condition     = var.max_workers >= 1 && var.max_workers <= 10
    error_message = "Max workers must be between 1 and 10"
  }
}

# Cloud Run Configuration
variable "cpu_limit" {
  description = "CPU limit for Cloud Run Job"
  type        = string
  default     = "1"
}

variable "memory_limit" {
  description = "Memory limit for Cloud Run Job"
  type        = string
  default     = "1Gi"
}

variable "job_timeout" {
  description = "Timeout for job execution"
  type        = string
  default     = "900s"  # 15 minutes
}

variable "job_max_retries" {
  description = "Maximum retries for failed job"
  type        = number
  default     = 1
}

# Scheduler Configuration
variable "schedule_cron" {
  description = "Cron expression for job schedule"
  type        = string
  default     = "0 6 * * *"  # Daily at 6 AM
}

variable "schedule_timezone" {
  description = "Timezone for scheduled execution"
  type        = string
  default     = "America/Chicago"
}