-- Drop existing table if it exists
DROP TABLE IF EXISTS job_listings CASCADE;

-- Create job_listings table matching USAJobs API structure
CREATE TABLE job_listings (
    -- Primary identifier
    position_id VARCHAR(100) PRIMARY KEY,  -- MatchedObjectId from API
    
    -- Core position information
    position_title VARCHAR(500) NOT NULL,
    position_uri VARCHAR(1000),
    
    -- Location (store as JSONB for flexibility since it's an array)
    position_location JSONB,  -- Full location array
    city_name VARCHAR(255),   -- Extracted for Chicago searches
    state_code VARCHAR(100),  -- For state-level queries
    
    -- Organization info
    organization_name VARCHAR(500),
    department_name VARCHAR(500),
    
    -- Salary/Remuneration (JSONB since it can have multiple ranges)
    position_remuneration JSONB,
    min_salary INTEGER,  -- Extracted minimum for queries
    max_salary INTEGER,  -- Extracted maximum for queries
    
    -- Dates
    position_start_date DATE,
    position_end_date DATE,
    publication_start_date DATE,
    application_close_date DATE,
    
    -- Job details
    job_summary TEXT,
    job_category JSONB,  -- Array of categories
    job_grade JSONB,     -- Array of grades
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    etl_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_city_name ON job_listings(city_name);
CREATE INDEX idx_state_code ON job_listings(state_code);
CREATE INDEX idx_organization ON job_listings(organization_name);
CREATE INDEX idx_salary_range ON job_listings(min_salary, max_salary);
CREATE INDEX idx_etl_timestamp ON job_listings(etl_timestamp);
CREATE INDEX idx_position_location ON job_listings USING GIN (position_location);

-- ETL metadata table
CREATE TABLE IF NOT EXISTS etl_runs (
    run_id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    status VARCHAR(50),
    error_message TEXT
);