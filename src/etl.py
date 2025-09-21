"""
etl.py - USAJobs ETL for Cloud Run Jobs
This runs as a containerized job, not a function
"""

import os
import sys
import json
import logging
import requests
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional

# Configure logging for Cloud Run
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class USAJobsETL:
    def __init__(self):
        """Initialize ETL with environment variables"""
        self.api_key = os.environ.get('USAJOBS_API_KEY')
        self.database_url = os.environ.get('DATABASE_URL')
        self.api_base_url = os.environ.get('USAJOBS_API_URL')
        self.default_location = os.environ.get('DEFAULT_LOCATION')
        self.keyword = os.environ.get('KEYWORD')
        
        if not self.api_key:
            raise ValueError("USAJOBS_API_KEY environment variable required")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable required")
    
    def fetch_jobs_from_api(self, page: int = 1) -> Optional[Dict]:
        """Fetch jobs from USAJobs API"""
        headers = {
            'Authorization-Key': self.api_key
        }
        
        params = {
            'Keyword': self.keyword,
            'LocationName': self.default_location,
            'ResultsPerPage': 100,
            'Page': page
        }
        
        try:
            logger.info(f"Fetching page {page} for keyword: {self.keyword}")
            response = requests.get(self.api_base_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API Error: {e}")
            return None

    def fetch_jobs_from_api_with_retry(self, page: int = 1, max_retries: int = 3) -> Optional[Dict]:
        """Fetch with exponential backoff"""
        for attempt in range(max_retries):
            try:
                response = self.fetch_jobs_from_api(page)
                if response:
                    return response
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"Retry {attempt + 1} after {wait_time}s")
                time.sleep(wait_time)
    return None
    
    def parse_job_listing(self, job_item: Dict) -> Optional[Dict]:
        """Parse single job from API response"""
        try:
            descriptor = job_item.get('MatchedObjectDescriptor', {})
            
            # Extract location info
            locations = descriptor.get('PositionLocation', [])
            first_location = locations[0] if locations else {}
            
            # Extract salary info  
            remunerations = descriptor.get('PositionRemuneration', [])
            first_remuneration = remunerations[0] if remunerations else {}
            
            # Parse salary values safely
            min_salary = None
            max_salary = None
            if first_remuneration:
                try:
                    min_salary = int(float(first_remuneration.get('MinimumRange', 0)))
                    max_salary = int(float(first_remuneration.get('MaximumRange', 0)))
                except (ValueError, TypeError):
                    pass
            
            return {
                'position_id': job_item.get('MatchedObjectId'),
                'position_title': descriptor.get('PositionTitle'),
                'position_uri': descriptor.get('PositionURI'),
                'position_location': Json(locations),
                'city_name': first_location.get('CityName'),
                'state_code': first_location.get('CountrySubDivisionCode'),
                'organization_name': descriptor.get('OrganizationName'),
                'department_name': descriptor.get('DepartmentName'),
                'position_remuneration': Json(remunerations),
                'min_salary': min_salary,
                'max_salary': max_salary,
                'position_start_date': descriptor.get('PositionStartDate'),
                'position_end_date': descriptor.get('PositionEndDate'),
                'publication_start_date': descriptor.get('PublicationStartDate'),
                'application_close_date': descriptor.get('ApplicationCloseDate'),
                'job_summary': descriptor.get('UserArea', {}).get('Details', {}).get('JobSummary', ''),
                'job_category': Json(descriptor.get('JobCategory', [])),
                'job_grade': Json(descriptor.get('JobGrade', []))
            }
        except Exception as e:
            logger.error(f"Error parsing job {job_item.get('MatchedObjectId')}: {e}")
            return None
    
    def upsert_job(self, conn, job_data: Dict) -> bool:
        """Insert or update job listing"""
        query = """
            INSERT INTO job_listings (
                position_id, position_title, position_uri, position_location,
                city_name, state_code, organization_name, department_name,
                position_remuneration, min_salary, max_salary,
                position_start_date, position_end_date,
                publication_start_date, application_close_date,
                job_summary, job_category, job_grade
            ) VALUES (
                %(position_id)s, %(position_title)s, %(position_uri)s, %(position_location)s,
                %(city_name)s, %(state_code)s, %(organization_name)s, %(department_name)s,
                %(position_remuneration)s, %(min_salary)s, %(max_salary)s,
                %(position_start_date)s, %(position_end_date)s,
                %(publication_start_date)s, %(application_close_date)s,
                %(job_summary)s, %(job_category)s, %(job_grade)s
            )
            ON CONFLICT (position_id) 
            DO UPDATE SET
                position_title = EXCLUDED.position_title,
                position_uri = EXCLUDED.position_uri,
                position_location = EXCLUDED.position_location,
                city_name = EXCLUDED.city_name,
                min_salary = EXCLUDED.min_salary,
                max_salary = EXCLUDED.max_salary,
                updated_at = CURRENT_TIMESTAMP,
                etl_timestamp = CURRENT_TIMESTAMP
            RETURNING position_id;
        """
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, job_data)
                return True
        except Exception as e:
            logger.error(f"Database error for job {job_data.get('position_id')}: {e}")
            return False
    
    def check_tables_exist(self, conn) -> bool:
        """Check if required tables exist"""
        query = """
            SELECT COUNT(*) as table_count
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('job_listings', 'etl_runs');
        """
        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return result[0] == 2  # Both tables should exist
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False

    def initialize_database(self, conn):
        """Initialize database using init.sql if tables don't exist"""
        init_sql_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'init_scripts', 'init.sql')

        if not os.path.exists(init_sql_path):
            raise FileNotFoundError(f"Database initialization file not found: {init_sql_path}")

        logger.info("Initializing database schema...")
        try:
            with open(init_sql_path, 'r') as file:
                init_sql = file.read()

            with conn.cursor() as cursor:
                cursor.execute(init_sql)
            conn.commit()
            logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            conn.rollback()
            raise

    def log_etl_run(self, conn, status: str, stats: Dict):
        """Log ETL run metadata"""
        query = """
            INSERT INTO etl_runs (
                completed_at, records_processed, records_inserted,
                records_updated, records_failed, status
            ) VALUES (
                CURRENT_TIMESTAMP, %(processed)s, %(inserted)s,
                %(updated)s, %(failed)s, %(status)s
            );
        """
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, {
                    'processed': stats.get('processed', 0),
                    'inserted': stats.get('inserted', 0),
                    'updated': stats.get('updated', 0),
                    'failed': stats.get('failed', 0),
                    'status': status
                })
        except Exception as e:
            logger.error(f"Failed to log ETL run: {e}")
    
    def run(self):
        """Main ETL process"""
        conn = None
        stats = {'processed': 0, 'inserted': 0, 'updated': 0, 'failed': 0}
        
        try:
            # Connect to database
            logger.info("Connecting to database...")
            conn = psycopg2.connect(self.database_url)
            conn.autocommit = False

            # Check if required tables exist, initialize if needed
            if not self.check_tables_exist(conn):
                logger.info("Required tables not found, initializing database...")
                self.initialize_database(conn)
            else:
                logger.info("Database tables exist, proceeding with ETL...")
            
            # Fetch all pages
            page = 1
            total_jobs = 0
            
            while True:
                api_response = self.fetch_jobs_from_api_with_retry(page=page)
                if not api_response:
                    break
                
                search_result = api_response.get('SearchResult', {})
                items = search_result.get('SearchResultItems', [])
                
                if not items:
                    logger.info("No more results")
                    break
                
                logger.info(f"Processing {len(items)} jobs from page {page}")
                
                # Process each job
                for item in items:
                    stats['processed'] += 1
                    job_data = self.parse_job_listing(item)
                    
                    if job_data and job_data.get('position_id'):
                        if self.upsert_job(conn, job_data):
                            stats['inserted'] += 1
                        else:
                            stats['failed'] += 1
                    else:
                        stats['failed'] += 1
                        logger.warning(f"Skipped job due to parsing error")
                
                # Commit batch
                conn.commit()
                total_jobs += len(items)
                
                # Check if more pages exist
                total_count = search_result.get('SearchResultCountAll', 0)
                if total_jobs >= total_count or page >= 10:  # Limit to 10 pages
                    break
                
                page += 1
            
            # Log successful run
            self.log_etl_run(conn, 'SUCCESS', stats)
            conn.commit()
            
            logger.info(f"ETL completed successfully. Stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"ETL failed: {e}")
            if conn:
                conn.rollback()
                self.log_etl_run(conn, 'FAILED', stats)
                conn.commit()
            raise
        finally:
            if conn:
                conn.close()

def main():
    """Entry point for Cloud Run Jobs"""
    try:
        logger.info("Starting USAJobs ETL process...")
        etl = USAJobsETL()
        stats = etl.run()
        logger.info(f"ETL completed: {stats}")
        return 0
    except Exception as e:
        logger.error(f"ETL failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())