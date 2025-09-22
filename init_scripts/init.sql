DROP TABLE IF EXISTS job_listings CASCADE;

CREATE TABLE job_listings (
    position_id VARCHAR(100) PRIMARY KEY,
    
    position_title VARCHAR(500) NOT NULL,
    position_uri VARCHAR(1000),
    
    position_location JSONB,
    city_name VARCHAR(255),
    state_code VARCHAR(100),
    
    organization_name VARCHAR(500),
    department_name VARCHAR(500),
    
    position_remuneration JSONB,
    min_salary INTEGER,
    max_salary INTEGER,
    
    position_start_date DATE,
    position_end_date DATE,
    publication_start_date DATE,
    application_close_date DATE,
    
    job_summary TEXT,
    job_category JSONB,
    job_grade JSONB
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    etl_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_city_name ON job_listings(city_name);
CREATE INDEX idx_state_code ON job_listings(state_code);
CREATE INDEX idx_organization ON job_listings(organization_name);
CREATE INDEX idx_salary_range ON job_listings(min_salary, max_salary);
CREATE INDEX idx_etl_timestamp ON job_listings(etl_timestamp);
CREATE INDEX idx_position_location ON job_listings USING GIN (position_location);

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