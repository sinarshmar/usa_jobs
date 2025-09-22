"""
etl.py - USAJobs ETL for Cloud Run Jobs
Extracts data engineering jobs available in Chicago from USAJobs API
Handles multi-location job postings correctly
"""

import os
import sys
import json
import logging
import requests
import psycopg2
import time
from psycopg2.extras import Json, RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration constants for ETL pipeline"""
    # API Settings - now from environment
    DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', 100))
    MAX_PAGES = int(os.environ.get('MAX_PAGES', 10))
    MAX_RETRIES = int(os.environ.get('MAX_RETRIES', 3))
    
    # Exponential backoff settings
    INITIAL_RETRY_DELAY = float(os.environ.get('INITIAL_RETRY_DELAY', 1))
    MAX_RETRY_DELAY = float(os.environ.get('MAX_RETRY_DELAY', 60))
    
    # Database settings
    BATCH_COMMIT_SIZE = int(os.environ.get('BATCH_COMMIT_SIZE', 100))
    
    # Rate limiting
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))
    MIN_REQUEST_INTERVAL = float(os.environ.get('MIN_REQUEST_INTERVAL', 0.5))
    
    # Feature flags
    DRY_RUN_MODE = os.environ.get('DRY_RUN_MODE', 'false').lower() == 'true'

class USAJobsETL:
    def __init__(self):
        """Initialize ETL with environment variables"""
        self.api_key = os.environ.get('USAJOBS_API_KEY')
        self.database_url = os.environ.get('DATABASE_URL')
        self.api_base_url = os.environ.get('USAJOBS_API_URL', 'https://data.usajobs.gov/api/search')
        self.default_location = os.environ.get('DEFAULT_LOCATION', 'Chicago')
        self.keyword = os.environ.get('KEYWORD', 'data engineering')
        
        # Validate required configuration
        if not self.api_key:
            raise ValueError("USAJOBS_API_KEY environment variable required")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable required")
        
        # Security: Validate API key format (basic check)
        if self.api_key and len(self.api_key) < 20:
            logger.warning("API key format appears invalid - please verify")
        
        # Security: Log configuration without exposing secrets
        if self.api_key:
            masked_key = self.api_key[:4] + '...' + self.api_key[-4:] if len(self.api_key) > 8 else 'HIDDEN'
            logger.info(f"Configuration loaded - API key: {masked_key}")
        
        # Log non-sensitive configuration
        logger.info(f"Target location: {self.default_location}, Keyword: {self.keyword}")
    
    def fetch_jobs_from_api_with_retry(self, page: int = 1, max_retries: int = None) -> Optional[Dict]:
        """Fetch jobs from USAJobs API with retry logic"""
        if max_retries is None:
            max_retries = Config.MAX_RETRIES
            
        headers = {
            'Authorization-Key': self.api_key
        }
        
        params = {
            'Keyword': self.keyword,
            'LocationName': self.default_location,
            'ResultsPerPage': Config.DEFAULT_PAGE_SIZE,
            'Page': page
        }
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching page {page} for keyword: '{self.keyword}', location: '{self.default_location}'")
                response = requests.get(
                    self.api_base_url, 
                    headers=headers, 
                    params=params, 
                    timeout=Config.REQUEST_TIMEOUT
                )
                
                if response.status_code == 429:  # Rate limited
                    wait_time = min(Config.INITIAL_RETRY_DELAY * (2 ** attempt), Config.MAX_RETRY_DELAY)
                    logger.warning(f"Rate limited. Retry {attempt + 1} after {wait_time}s")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                
                # Add small delay between successful requests to be respectful
                time.sleep(Config.MIN_REQUEST_INTERVAL)
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    logger.error(f"API Error after {max_retries} attempts: {e}")
                    return None
                wait_time = min(Config.INITIAL_RETRY_DELAY * (2 ** attempt), Config.MAX_RETRY_DELAY)
                logger.warning(f"API error, retry {attempt + 1} after {wait_time}s: {e}")
                time.sleep(wait_time)
        
        return None
    
    def parse_job_listing(self, job_item: Dict) -> Optional[Dict]:
        """
        Parse job from API response - handle multi-location postings
        Note: Most USAJobs postings are multi-location "Public Notices"
        """
        try:
            descriptor = job_item.get('MatchedObjectDescriptor', {})
            
            # Extract all locations
            locations = descriptor.get('PositionLocation', [])
            if not locations:
                return None
            
            # Check if Chicago is among the locations
            chicago_location = None
            has_chicago = False
            
            for loc in locations:
                city_name = str(loc.get('CityName', '')).lower()
                location_name = str(loc.get('LocationName', '')).lower()
                
                if 'chicago' in city_name or 'chicago' in location_name:
                    has_chicago = True
                    chicago_location = loc
                    break
            
            # Skip jobs that don't include Chicago
            if not has_chicago:
                logger.debug(f"Skipping non-Chicago job {job_item.get('MatchedObjectId')} - {descriptor.get('PositionTitle')}")
                return None
            
            # If no specific Chicago location found but has Chicago, use first location
            if not chicago_location and locations:
                chicago_location = locations[0]
            
            # Check if this is a nationwide/multi-location posting
            location_display = descriptor.get('PositionLocationDisplay', '')
            is_multi_location = len(locations) > 1
            is_nationwide = 'various' in location_display.lower() or len(locations) > 10
            
            # Log multi-location jobs for transparency
            if is_multi_location:
                logger.debug(f"Job {job_item.get('MatchedObjectId')} has {len(locations)} locations including Chicago")
            
            # Extract salary info (PA = Per Annum)
            remunerations = descriptor.get('PositionRemuneration', [])
            first_remuneration = remunerations[0] if remunerations else {}
            
            min_salary = None
            max_salary = None
            if first_remuneration:
                try:
                    min_salary = int(float(first_remuneration.get('MinimumRange', 0)))
                    max_salary = int(float(first_remuneration.get('MaximumRange', 0)))
                except (ValueError, TypeError):
                    pass
            
            # Parse dates safely
            def parse_date(date_str):
                if date_str:
                    try:
                        # Handle USAJobs datetime format
                        return date_str.split('T')[0] if 'T' in date_str else date_str
                    except:
                        return None
                return None
            
            return {
                'position_id': job_item.get('MatchedObjectId'),
                'position_title': descriptor.get('PositionTitle'),
                'position_uri': descriptor.get('PositionURI'),
                'position_location': Json([chicago_location] if chicago_location else []),
                'city_name': chicago_location.get('CityName', 'Chicago') if chicago_location else 'Chicago',
                'state_code': chicago_location.get('CountrySubDivisionCode', 'Illinois') if chicago_location else 'Illinois',
                'organization_name': descriptor.get('OrganizationName'),
                'department_name': descriptor.get('DepartmentName'),
                'position_remuneration': Json(remunerations),
                'min_salary': min_salary,
                'max_salary': max_salary,
                'position_start_date': parse_date(descriptor.get('PositionStartDate')),
                'position_end_date': parse_date(descriptor.get('PositionEndDate')),
                'publication_start_date': parse_date(descriptor.get('PublicationStartDate')),
                'application_close_date': parse_date(descriptor.get('ApplicationCloseDate')),
                'job_summary': descriptor.get('UserArea', {}).get('Details', {}).get('JobSummary', '') if descriptor.get('UserArea') else '',
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
                state_code = EXCLUDED.state_code,
                min_salary = EXCLUDED.min_salary,
                max_salary = EXCLUDED.max_salary,
                application_close_date = EXCLUDED.application_close_date,
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
                return result[0] == 2
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False

    def initialize_database(self, conn):
        """Initialize database using init.sql if tables don't exist"""
        init_sql_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'init_scripts', 'init.sql')

        # If running in container, check alternative path
        if not os.path.exists(init_sql_path):
            init_sql_path = '/app/init_scripts/init.sql'
        
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
                records_updated, records_failed, status, error_message
            ) VALUES (
                CURRENT_TIMESTAMP, %(processed)s, %(inserted)s,
                %(updated)s, %(failed)s, %(status)s, %(error_message)s
            );
        """
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, {
                    'processed': stats.get('processed', 0),
                    'inserted': stats.get('inserted', 0),
                    'updated': stats.get('updated', 0),
                    'failed': stats.get('failed', 0),
                    'status': status,
                    'error_message': stats.get('error_message')
                })
        except Exception as e:
            logger.error(f"Failed to log ETL run: {e}")
    
    def run(self):
        """Main ETL process"""
        conn = None
        stats = {
            'processed': 0, 
            'inserted': 0, 
            'updated': 0, 
            'failed': 0,
            'skipped_non_chicago': 0,
            'error_message': None
        }
        
        try:
            # Connect to database
            logger.info("="*60)
            logger.info("Starting USAJobs ETL Process")
            logger.info(f"Configuration: Keyword='{self.keyword}', Location='{self.default_location}'")
            logger.info("="*60)
            
            logger.info("Connecting to database...")
            conn = psycopg2.connect(self.database_url)
            conn.autocommit = False

            # Initialize database if needed
            if not self.check_tables_exist(conn):
                logger.info("Required tables not found, initializing database...")
                self.initialize_database(conn)
            else:
                logger.info("Database tables verified, proceeding with ETL...")
            
            # Fetch all pages (analysis shows only 22 total results)
            page = 1
            total_jobs = 0
            chicago_jobs = 0
            max_pages = 5  # Reasonable limit based on analysis
            
            while page <= max_pages:
                api_response = self.fetch_jobs_from_api_with_retry(page=page)
                if not api_response:
                    logger.warning(f"Failed to fetch page {page}, stopping pagination")
                    break
                
                search_result = api_response.get('SearchResult', {})
                items = search_result.get('SearchResultItems', [])
                total_available = search_result.get('SearchResultCountAll', 0)
                
                if not items:
                    logger.info("No more results to process")
                    break
                
                logger.info(f"Page {page}: Processing {len(items)} jobs (Total available: {total_available})")
                
                # Process each job
                for item in items:
                    stats['processed'] += 1
                    job_data = self.parse_job_listing(item)
                    
                    if job_data is None:
                        stats['skipped_non_chicago'] += 1
                        continue
                    
                    chicago_jobs += 1
                    if job_data.get('position_id'):
                        if self.upsert_job(conn, job_data):
                            stats['inserted'] += 1
                            logger.debug(f"Upserted job {job_data.get('position_id')}: {job_data.get('position_title')[:50]}")
                        else:
                            stats['failed'] += 1
                    else:
                        stats['failed'] += 1
                        logger.warning("Skipped job due to missing position_id")
                
                # Commit after each page
                conn.commit()
                total_jobs += len(items)
                
                # Check if we've fetched all available jobs
                if total_jobs >= total_available:
                    logger.info(f"Fetched all {total_available} available jobs")
                    break
                
                page += 1
            
            # Log successful run
            self.log_etl_run(conn, 'SUCCESS', stats)
            conn.commit()
            
            # Final summary
            logger.info("="*60)
            logger.info("ETL COMPLETED SUCCESSFULLY")
            logger.info(f"Total jobs processed: {stats['processed']}")
            percentage = (chicago_jobs*100/stats['processed']) if stats['processed'] > 0 else 0
            logger.info(f"Chicago jobs found: {chicago_jobs} ({percentage:.1f}% of total)")
            logger.info(f"Jobs inserted/updated: {stats['inserted']}")
            logger.info(f"Non-Chicago jobs skipped: {stats['skipped_non_chicago']}")
            logger.info(f"Failed: {stats['failed']}")
            logger.info("Note: Most jobs are multi-location postings that include Chicago")
            logger.info("="*60)
            
            return stats
            
        except Exception as e:
            logger.error(f"ETL failed with error: {e}")
            stats['error_message'] = str(e)
            if conn:
                conn.rollback()
                self.log_etl_run(conn, 'FAILED', stats)
                conn.commit()
            raise
        finally:
            if conn:
                conn.close()
                logger.info("Database connection closed")

def main():
    """Entry point for both local and Cloud Run execution"""
    try:
        etl = USAJobsETL()
        stats = etl.run()
        return 0 if stats.get('inserted', 0) > 0 or stats.get('processed', 0) > 0 else 1
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())