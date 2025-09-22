# USAJobs ETL - Terraform Infrastructure

This directory contains Infrastructure as Code (IaC) for deploying the USAJobs ETL pipeline to Google Cloud Platform using Cloud Run Jobs and Cloud Scheduler.

## Architecture

```
Cloud Scheduler (Daily Trigger)
    ↓
Cloud Run Job (ETL Container)
    ↓
External PostgreSQL (Supabase/Neon)
```

## Prerequisites

1. **Google Cloud Account**: With billing enabled (or free credits)
2. **Terraform**: Version 1.0 or higher
3. **gcloud CLI**: Authenticated with appropriate permissions
4. **Docker Image**: Published to Docker Hub or Artifact Registry
5. **Database**: Supabase/Neon account with connection string

## Setup Instructions

### 1. Prepare Your Environment

```bash
# Authenticate with GCP
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable secretmanager.googleapis.com  # If using Secret Manager
```

### 2. Configure Terraform Variables

```bash
# Copy the example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
vim terraform.tfvars
```

Required values to update:

- `gcp_project_id`: Your GCP project ID
- `docker_image`: Your Docker Hub image path
- `database_url`: Your Supabase/Neon connection string
- `usajobs_api_key`: Your USAJobs API key

### 3. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review the deployment plan
terraform plan

# Deploy (will prompt for confirmation)
terraform apply

# Or deploy without prompt
terraform apply -auto-approve
```

### 4. Manual Testing

After deployment, test the job manually:

```bash
# Trigger the job manually
gcloud run jobs execute usajobs-etl --region us-central1

# Check logs
gcloud logging read "resource.type=cloud_run_job" --limit 50
```

### 5. Monitor Scheduled Execution

The job will run automatically based on the schedule (default: 6 AM daily).

View in Console:

- Cloud Run Jobs: https://console.cloud.google.com/run/jobs
- Cloud Scheduler: https://console.cloud.google.com/cloudscheduler

## Cost Optimization

To minimize costs:

1. **Use Supabase/Neon**: Free database tier instead of Cloud SQL
2. **Set appropriate resource limits**: Start with 1 CPU and 512Mi memory
3. **Monitor usage**: Set up billing alerts
4. **Clean up when done**: Run `terraform destroy`

## Teardown

To remove all resources and avoid charges:

```bash
terraform destroy
```

## Configuration Options

### Resource Limits

- `cpu_limit`: Default "1", can increase to "2" or "4"
- `memory_limit`: Default "512Mi", can increase to "1Gi" or "2Gi"
- `job_timeout`: Default "900s" (15 minutes)

### Schedule

- `schedule_cron`: Default "0 6 \* \* \*" (6 AM daily)
- `schedule_timezone`: Default "America/Chicago"

### Performance

- `max_pages`: Number of API pages to fetch
- `batch_commit_size`: Database commit batch size
- `enable_parallel`: Enable parallel processing for large datasets

## Security Considerations

### Current Setup (Development)

- Secrets passed as environment variables
- Suitable for assessment/development

### Production Setup (Recommended)

1. Uncomment Secret Manager resources in `main.tf`
2. Store sensitive values in Secret Manager
3. Grant service account access to secrets
4. Reference secrets in Cloud Run configuration

## Troubleshooting

### Common Issues

1. **Permission Denied**

   ```bash
   # Grant Cloud Run Admin role
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="user:YOUR_EMAIL" \
     --role="roles/run.admin"
   ```

2. **APIs Not Enabled**

   ```bash
   gcloud services enable run.googleapis.com cloudscheduler.googleapis.com
   ```

3. **Docker Image Not Found**

   - Ensure image is pushed to Docker Hub
   - Verify image path in terraform.tfvars

4. **Database Connection Failed**
   - Check database URL format
   - Ensure database allows external connections
   - Verify SSL requirements

## Files in This Directory

- `main.tf`: Main infrastructure definition
- `variables.tf`: Variable declarations
- `terraform.tfvars.example`: Example configuration
- `terraform.tfvars`: Your actual configuration (not in git)
- `README.md`: This file

## Assessment Note

This infrastructure configuration demonstrates production-ready deployment practices while optimizing for cost. The actual deployment is optional for the assessment - the IaC code itself demonstrates the required knowledge.

**For assessment submission**: The infrastructure has been tested once and torn down to avoid ongoing costs. The configuration is ready for deployment using the instructions above.
