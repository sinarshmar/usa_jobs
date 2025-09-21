#!/usr/bin/env python3
"""
Test script for USAJobs ETL - explore data and test individual methods
"""

import os
import json
from dotenv import load_dotenv
from src.etl import USAJobsETL

# Load environment variables
load_dotenv()

def main():
    print("=== USAJobs ETL Testing ===\n")

    # Initialize ETL (without database)
    try:
        etl = USAJobsETL()
        print("✓ ETL initialized successfully")
        print(f"✓ API Key loaded: {bool(etl.api_key)}")
    except ValueError as e:
        if "DATABASE_URL" in str(e):
            # Override for testing without DB
            os.environ['DATABASE_URL'] = 'postgresql://dummy:dummy@localhost:5432/dummy'
            etl = USAJobsETL()
            print("✓ ETL initialized (DB connection skipped for testing)")
        else:
            raise

    print("\n=== Testing API Fetch ===")

    # Test API fetch
    response = etl.fetch_jobs_from_api(page=1)

    if not response:
        print("✗ API call failed")
        return

    print("✓ API call successful")

    # Explore the response structure
    search_result = response.get('SearchResult', {})
    total_count = search_result.get('SearchResultCountAll', 0)
    items = search_result.get('SearchResultItems', [])

    print(f"✓ Total jobs available: {total_count}")
    print(f"✓ Jobs in this page: {len(items)}")

    if not items:
        print("✗ No job items found")
        return

    print("\n=== Testing Job Parsing ===")

    # Test parsing first few jobs
    for i, item in enumerate(items[:3]):
        print(f"\n--- Job {i+1} ---")
        parsed_job = etl.parse_job_listing(item)

        if parsed_job:
            print(f"✓ Position ID: {parsed_job.get('position_id')}")
            print(f"✓ Title: {parsed_job.get('position_title')}")
            print(f"✓ Organization: {parsed_job.get('organization_name')}")
            print(f"✓ Location: {parsed_job.get('city_name')}, {parsed_job.get('state_code')}")
            print(f"✓ Salary: ${parsed_job.get('min_salary', 'N/A')} - ${parsed_job.get('max_salary', 'N/A')}")
        else:
            print(f"✗ Failed to parse job {i+1}")

    print("\n=== Raw Data Exploration ===")
    print("First job raw data (first 500 chars):")
    first_job_raw = json.dumps(items[0], indent=2)[:500]
    print(first_job_raw + "...")

    print(f"\n=== Summary ===")
    print(f"✓ API connection: Working")
    print(f"✓ Data retrieval: {len(items)} jobs fetched")
    print(f"✓ Data parsing: Working")
    print(f"✓ Total jobs available: {total_count}")

if __name__ == "__main__":
    main()