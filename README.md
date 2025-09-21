# USAJobs ETL Pipeline

A phased ETL pipeline implementation for the Tasman Senior Data Engineer Assessment. This project extracts job postings from the USAJobs API, transforms the data, and loads it into a PostgreSQL database.

## Project Overview

This implementation follows a phased development approach:

- **Phase 1: Local MVP** (Current) - Basic ETL functionality with local database
- **Phase 2: Production Hardening** - Error handling and modular architecture
- **Phase 3: Containerization** - Docker packaging
- **Phase 4: Cloud Deployment** - Infrastructure as Code and cloud setup
- **Phase 5: Testing & Documentation** - Comprehensive testing and docs

## Phase 1: Local MVP

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- USAJobs API key

### Quick Start

1. **Clone and setup**:

   ```bash
   git clone <repository-url>
   cd USA_jobs
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Start local database**:

   ```bash
   docker-compose up -d
   ```

3. **Set API key**:

   ```bash
   export USAJOBS_API_KEY="your-api-key-here"
   ```

4. **Run ETL process**:

   ```bash
   python src/etl.py
   ```

5. **Verify results**:
   ```bash
   docker-compose exec postgres psql -U user -d jobs -c "SELECT COUNT(*) FROM job_listings;"
   ```

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

### Troubleshooting

**Database connection issues**:

- Ensure Docker is running: `docker ps`
- Check PostgreSQL logs: `docker-compose logs postgres`

**API connection issues**:

- Verify API key is set: `echo $USAJOBS_API_KEY`
- Test API manually: `curl -H "Authorization-Key: $USAJOBS_API_KEY" "https://data.usajobs.gov/api/search?Keyword=data%20engineering"`

**No data inserted**:

- Check console output for errors
- Verify API response format hasn't changed
- Check database table exists: `docker-compose exec postgres psql -U user -d jobs -c "\dt"`

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
