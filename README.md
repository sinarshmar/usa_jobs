# USAJobs ETL Pipeline

Production-ready ETL pipeline that extracts data engineering jobs from USAJobs API and loads them into PostgreSQL. Features automated cloud deployment with Secret Manager security and daily scheduling.

## 🚀 Quick Start

### Local Development

```bash
# 1. Clone and setup
git clone <repository-url>
cd USA_jobs
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your USAJobs API key and database URL

# 3. Start local database
docker-compose up -d

# 4. Run ETL
python src/etl.py
```

### Cloud Deployment (GCP)

```bash
# Prerequisites: gcloud CLI, Terraform, Docker
# 1. Configure GCP
gcloud auth login
gcloud auth application-default login

# 2. Update configuration
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project details

# 3. Deploy
terraform init
terraform apply
```

## 📋 Prerequisites

**Local Development:**
- Python 3.11+
- Docker and Docker Compose
- USAJobs API key ([Get one here](https://developer.usajobs.gov/APIRequest))

**Cloud Deployment:**
- Google Cloud CLI (`gcloud`)
- Terraform
- Docker
- GCP Project with billing enabled

## 🏗️ Architecture

### Local Development
```
.env file → Python ETL → PostgreSQL (Docker)
```
- Configuration via `.env` file
- Local PostgreSQL via `docker-compose`
- Direct environment variable access

### Production Deployment
```
Terraform → Secret Manager → Cloud Run Jobs → Supabase → Cloud Scheduler
```
- **No `.env` files** - secrets managed by Google Secret Manager
- **Infrastructure as Code** - Terraform manages all resources
- **Automated scheduling** - Cloud Scheduler triggers daily runs
- **Enterprise security** - IAM roles and secret access controls

## 🔐 Production Security Model

**Why different approaches for local vs production?**

| Aspect | Local Development | Production |
|--------|------------------|------------|
| **Secrets** | `.env` file (excluded from git) | Google Secret Manager |
| **Database** | Docker container | Managed Supabase |
| **Deployment** | Manual `python` command | Automated Cloud Run Jobs |
| **Scheduling** | Manual execution | Cloud Scheduler (daily) |
| **Security** | Developer responsibility | IAM + Secret Manager |

**Benefits of this architecture:**
- ✅ **Security**: No secrets in containers or environment variables
- ✅ **Auditability**: All secret access logged by Google Cloud
- ✅ **Scalability**: Cloud Run scales automatically
- ✅ **Reliability**: Managed services with SLA guarantees
- ✅ **Cost**: Pay-per-execution model

### Project Structure

```
USA_jobs/
├── src/
│   ├── __init__.py
│   └── etl.py                 # Main ETL script (Phase 1)
├── sql/
│   └── schema.sql             # Database schema
├── docker-compose.yml         # Local PostgreSQL setup
├── requirements.txt           # Python dependencies
├── .gitignore                # Git ignore rules
├── .env.example              # Environment variables template
└── README.md                 # This file
```

### Configuration

Create a `.env` file or set environment variables:

```bash
USAJOBS_API_KEY=your-api-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/jobs
```

### API Information

- **Endpoint**: https://data.usajobs.gov/api/search
- **Authentication**: Header "Authorization-Key: {api_key}"
- **Search**: Keyword "data engineering"
- **Documentation**: https://developer.usajobs.gov/

### Database Schema

The `job_listings` table includes:

- `position_id` (VARCHAR, PRIMARY KEY)
- `position_title` (VARCHAR, NOT NULL)
- `position_uri` (VARCHAR)
- `position_location` (JSONB)
- `position_remuneration` (JSONB)
- `created_at` (TIMESTAMP)
- `etl_timestamp` (TIMESTAMP)

## 🧪 Testing

The project includes comprehensive tests covering unit, integration, and database operations:

```bash
# Run all tests
python run_tests.py

# Or use pytest directly
pytest tests/ -v
```

**Test Coverage:**
- ✅ **Configuration loading and validation**
- ✅ **API response parsing and data transformation**
- ✅ **Database schema and operations**
- ✅ **End-to-end integration testing**
- ✅ **Error handling and edge cases**

## 🚀 Deployment Guide

### Local Development Setup
```bash
# 1. Clone repository
git clone <repo-url>
cd USA_jobs

# 2. Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Database
docker-compose up -d

# 4. Configuration
cp .env.example .env
# Add your USAJobs API key to .env

# 5. Run & Test
python src/etl.py
python run_tests.py
```

### Production Deployment
```bash
# 1. Prerequisites
gcloud auth login
gcloud auth application-default login

# 2. Configure project
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit with your GCP project details

# 3. Deploy infrastructure
terraform init
terraform apply

# 4. Verify deployment
gcloud run jobs execute usajobs-etl --region=europe-west2
```

### Troubleshooting

**Local Issues:**
- Database: `docker-compose logs postgres`
- API: `curl -H "Authorization-Key: $API_KEY" "https://data.usajobs.gov/api/search?Keyword=data%20engineering"`

**Production Issues:**
- Logs: `gcloud logging read 'resource.type=cloud_run_job'`
- Job status: `gcloud run jobs executions list --job=usajobs-etl --region=europe-west2`
- Secrets: `gcloud secrets list`

## Development Notes

### Phase 1 Implementation Details

- Single-file ETL script for simplicity
- Hardcoded configuration (will be externalized in Phase 2)
- Basic error handling with console output
- First page of API results only
- Simple duplicate handling with ON CONFLICT

### Known Limitations (Phase 1)

- No pagination handling (processes first page only)
- Limited error handling and retry logic
- No structured logging
- Hardcoded configuration values
- No automated tests

These limitations will be addressed in subsequent phases.

## Next Steps

After Phase 1 completion:

1. Commit changes: `git commit -m "Phase 1: Basic ETL with local database"`
2. Begin Phase 2: Production Hardening with modular architecture
3. Add comprehensive error handling and retry logic
4. Implement proper configuration management

## License

This project is created for the Tasman Senior Data Engineer Assessment.
