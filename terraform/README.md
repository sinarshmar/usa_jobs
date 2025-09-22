# Terraform Infrastructure

Infrastructure as Code for deploying USAJobs ETL to Google Cloud Platform.

## Quick Deploy

```bash
# 1. Configure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project details

# 2. Deploy
terraform init
terraform apply

# 3. Test
gcloud run jobs execute usajobs-etl --region=europe-west2
```

## Architecture

- **Cloud Run Jobs**: Containerized ETL execution
- **Cloud Scheduler**: Daily trigger at 6 AM
- **Secret Manager**: Secure credential management
- **Artifact Registry**: Private container registry

## Configuration

Update `terraform.tfvars` with:
- `gcp_project_id`: Your GCP project
- `database_url`: Supabase connection string
- `usajobs_api_key`: Your API key

## Cleanup

```bash
terraform destroy
```
