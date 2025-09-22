# main.tf - USAJobs ETL Infrastructure as Code
# This configuration deploys the ETL pipeline to Google Cloud Run Jobs
# with Cloud Scheduler for daily execution

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  # Backend configuration for state storage (optional)
  # Uncomment to use GCS for state management
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "usajobs-etl"
  # }
}

# Provider configuration
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Artifact Registry Repository (already created manually)
# This imports the existing repository rather than creating a new one
data "google_artifact_registry_repository" "etl_repo" {
  repository_id = "usajobs-etl-repo"
  location      = var.gcp_region
}

# Cloud Run Job for ETL execution
resource "google_cloud_run_v2_job" "usajobs_etl" {
  name     = "usajobs-etl"
  location = var.gcp_region
  
  template {
    parallelism = 1  # Single instance for ETL
    task_count  = 1  # Single task execution
    
    template {
      containers {
        image = var.docker_image
        
        # Environment variables from Secret Manager
        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url.secret_id
              version = "latest"
            }
          }
        }

        env {
          name = "USAJOBS_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.api_key.secret_id
              version = "latest"
            }
          }
        }
        
        env {
          name  = "DEFAULT_LOCATION"
          value = var.default_location
        }
        
        env {
          name  = "KEYWORD"
          value = var.keyword
        }
        
        env {
          name  = "LOG_LEVEL"
          value = var.log_level
        }
        
        # Performance settings
        env {
          name  = "MAX_PAGES"
          value = tostring(var.max_pages)
        }
        
        env {
          name  = "BATCH_COMMIT_SIZE"
          value = tostring(var.batch_commit_size)
        }
        
        env {
          name  = "ENABLE_PARALLEL"
          value = var.enable_parallel
        }
        
        env {
          name  = "MAX_WORKERS"
          value = tostring(var.max_workers)
        }
        
        # Resource limits
        resources {
          limits = {
            cpu    = var.cpu_limit
            memory = var.memory_limit
          }
        }
      }
      
      # Execution environment
      max_retries = var.job_max_retries
      timeout     = var.job_timeout  # Updated to task-timeout format
      
      service_account = google_service_account.etl_service_account.email
    }
  }
  
  lifecycle {
    ignore_changes = [
      client,
      client_version,
    ]
  }
}

# Service Account for Cloud Run Job
resource "google_service_account" "etl_service_account" {
  account_id   = "usajobs-etl-sa"
  display_name = "USAJobs ETL Service Account"
  description  = "Service account for USAJobs ETL Cloud Run Job"
}

# IAM binding for Cloud Run Job invoker
resource "google_cloud_run_v2_job_iam_binding" "etl_invoker" {
  name     = google_cloud_run_v2_job.usajobs_etl.name
  location = google_cloud_run_v2_job.usajobs_etl.location
  role     = "roles/run.invoker"
  
  members = [
    "serviceAccount:${google_service_account.scheduler_service_account.email}"
  ]
}

# Service Account for Cloud Scheduler
resource "google_service_account" "scheduler_service_account" {
  account_id   = "usajobs-etl-scheduler-sa"
  display_name = "USAJobs ETL Scheduler Service Account"
  description  = "Service account for Cloud Scheduler to trigger ETL job"
}

# Cloud Scheduler Job
resource "google_cloud_scheduler_job" "etl_schedule" {
  name        = "usajobs-etl-daily"
  description = "Daily trigger for USAJobs ETL pipeline"
  schedule    = var.schedule_cron
  time_zone   = var.schedule_timezone
  
  # Retry configuration for scheduler
  retry_config {
    retry_count          = 1
    max_retry_duration   = "60s"
    min_backoff_duration = "5s"
    max_backoff_duration = "3600s"
  }
  
  # HTTP target configuration to trigger Cloud Run Job
  http_target {
    http_method = "POST"
    uri         = "https://${var.gcp_region}-run.googleapis.com/v2/projects/${var.gcp_project_id}/locations/${var.gcp_region}/jobs/${google_cloud_run_v2_job.usajobs_etl.name}:run"
    
    oauth_token {
      service_account_email = google_service_account.scheduler_service_account.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }
}

# Grant Cloud Scheduler permission to trigger Cloud Run Job
resource "google_project_iam_member" "scheduler_run_invoker" {
  project = var.gcp_project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.scheduler_service_account.email}"
}

# Secret Manager for sensitive values (production security)
resource "google_secret_manager_secret" "api_key" {
  secret_id = "usajobs-api-key"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "api_key_version" {
  secret      = google_secret_manager_secret.api_key.id
  secret_data = var.usajobs_api_key
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "database-url"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url_version" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = var.database_url
}

# Grant service account access to secrets
resource "google_secret_manager_secret_iam_member" "etl_sa_api_key_access" {
  secret_id = google_secret_manager_secret.api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.etl_service_account.email}"
}

resource "google_secret_manager_secret_iam_member" "etl_sa_database_url_access" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.etl_service_account.email}"
}

# Outputs for reference
output "cloud_run_job_name" {
  value       = google_cloud_run_v2_job.usajobs_etl.name
  description = "Name of the deployed Cloud Run Job"
}

output "cloud_run_job_uri" {
  value       = "https://console.cloud.google.com/run/jobs/details/${var.gcp_region}/${google_cloud_run_v2_job.usajobs_etl.name}"
  description = "Console URL for the Cloud Run Job"
}

output "scheduler_job_name" {
  value       = google_cloud_scheduler_job.etl_schedule.name
  description = "Name of the Cloud Scheduler job"
}

output "next_steps" {
  value = <<-EOT
    Deployment Instructions:
    1. Initialize Terraform: terraform init
    2. Review plan: terraform plan
    3. Deploy: terraform apply
    4. To destroy: terraform destroy
    
    Manual trigger:
    gcloud run jobs execute ${google_cloud_run_v2_job.usajobs_etl.name} --region ${var.gcp_region}
  EOT
  description = "Instructions for deployment and manual execution"
}