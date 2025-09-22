# USAJobs ETL Pipeline

Production-ready ETL pipeline that extracts data engineering jobs from USAJobs API and loads them into PostgreSQL. Features automated cloud deployment with Secret Manager security and daily scheduling.

## 🚀 Quick Start

### Local Development

```bash
# 1. Clone and setup
git clone https://github.com/sinarshmar/usa_jobs
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

| Aspect       | Local Development               | Production            |
| ------------ | ------------------------------- | --------------------- |
| **Secrets**  | `.env` file (excluded from git) | Google Secret Manager |
| **Database** | Docker container                | Managed Supabase      |

**Benefits of this architecture:**

- ✅ **Security**: No secrets in containers or environment variables
- ✅ **Auditability**: All secret access logged by Google Cloud

### Project Structure

```
USA_jobs/
├── src/
│   ├── __init__.py
│   └── etl.py                 # Main ETL script
├── tests/                     # Comprehensive test suite
│   ├── conftest.py
│   ├── test_database.py
│   ├── test_etl.py
│   └── test_integration.py
├── init_scripts/
│   └── init.sql               # Database schema
├── terraform/                 # Cloud infrastructure
│   ├── main.tf
│   ├── variables.tf
│   └── terraform.tfvars.example
├── docker-compose.yml         # Local PostgreSQL setup
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
└── README.md                 # This file
```

### Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Key environment variables:

- `USAJOBS_API_KEY` - Your USAJobs API key ([Get one here](https://developer.usajobs.gov/APIRequest))
- `DATABASE_URL` - PostgreSQL connection string
- `DEFAULT_LOCATION` - Target location (default: Chicago)
- `KEYWORD` - Job search keyword (default: "data engineering")
- `LOG_LEVEL` - Logging verbosity (INFO, DEBUG, etc.)

See `.env.example` for complete configuration options.

### Database Schema

The pipeline creates two main tables:

**`job_listings`** - Stores job posting data with:

- Core fields: position_id (PK), position_title, position_uri
- Location data: position_location (JSONB), city_name, state_code
- Organization: organization_name, department_name
- Compensation: position_remuneration (JSONB), min_salary, max_salary
- Dates: position_start_date, position_end_date, application_close_date
- Job details: job_summary, job_category (JSONB), job_grade (JSONB)
- Metadata: created_at, updated_at, etl_timestamp

**`etl_runs`** - Tracks ETL execution metadata and statistics

See `init_scripts/init.sql` for complete schema definition and indexes.

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

_Note: Comprehensive test suite was generated with Claude code._

## 🏛️ Design Decisions

### Architecture Choices

- **Single ETL file** - Appropriate for scope (one API, one database, ~22 records)
- **Sequential processing** - Sufficient for current dataset size
- **No orchestration tool** - Cloud Scheduler provides adequate scheduling
- **External database** - Supabase demonstrates cost optimization and avoids vendor lock-in

### Database Configuration

- **Local**: PostgreSQL via Docker Compose
- **Production**: Supabase free tier (no GCP costs)

### Security Model

- **Development**: `.env` files for convenience
- **Production**: Google Secret Manager, Cloud SQL Proxy, service accounts with minimal permissions

### Scalability Considerations

- Pagination limited to 5 pages (analysis showed only 22 total results)
- Parallel processing prepared but disabled (ENABLE_PARALLEL=false)
- Ready to scale with larger datasets when needed

### Areas for Future Enhancement

- Parallel processing for large datasets
- Data quality validation and monitoring
- Incremental ETL with change detection
- GitHub Actions with Terraform for CI/CD.

## License

This project is created for the Tasman Senior Data Engineer Assessment.
