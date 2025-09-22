"""
Test configuration and fixtures for USAJobs ETL
"""

import pytest
import os
import psycopg2
from unittest.mock import Mock
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture
def mock_api_response():
    """Mock USAJobs API response with realistic data"""
    return {
        "SearchResult": {
            "SearchResultCount": 2,
            "SearchResultItems": [
                {
                    "MatchedObjectDescriptor": {
                        "PositionID": "TEST-001",
                        "PositionTitle": "Senior Data Engineer",
                        "PositionURI": "https://test.usajobs.gov/job/TEST-001",
                        "PositionLocation": [
                            {
                                "LocationName": "Chicago, IL",
                                "CityName": "Chicago, IL",
                                "CountryCode": "United States",
                                "CountrySubDivisionCode": "Illinois",
                                "Longitude": -87.6298,
                                "Latitude": 41.8781
                            }
                        ],
                        "PositionRemuneration": [
                            {
                                "MinimumRange": "100000",
                                "MaximumRange": "150000",
                                "RateIntervalCode": "PA"
                            }
                        ],
                        "ApplicationCloseDate": "2025-10-01T00:00:00.0000"
                    }
                },
                {
                    "MatchedObjectDescriptor": {
                        "PositionID": "TEST-002",
                        "PositionTitle": "Data Engineering Specialist",
                        "PositionURI": "https://test.usajobs.gov/job/TEST-002",
                        "PositionLocation": [
                            {
                                "LocationName": "Remote",
                                "CityName": "Anywhere",
                                "CountryCode": "United States"
                            }
                        ],
                        "PositionRemuneration": [
                            {
                                "MinimumRange": "90000",
                                "MaximumRange": "120000",
                                "RateIntervalCode": "PA"
                            }
                        ],
                        "ApplicationCloseDate": "2025-09-30T00:00:00.0000"
                    }
                }
            ]
        }
    }

@pytest.fixture
def test_database_url():
    """Get test database URL from environment"""
    return os.environ.get('TEST_DATABASE_URL', os.environ.get('DATABASE_URL'))

@pytest.fixture
def mock_requests():
    """Mock requests module for API calls"""
    mock = Mock()
    mock.get.return_value.status_code = 200
    mock.get.return_value.json.return_value = {}
    return mock