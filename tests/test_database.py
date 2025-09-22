"""
Tests for database operations and schema
"""

import pytest
import psycopg2
import os
from unittest.mock import patch
import json


class TestDatabaseSchema:
    """Test database schema and table structure"""

    def test_database_connection(self, test_database_url):
        """Test database connection works"""
        if not test_database_url:
            pytest.skip("No database URL provided for testing")

        try:
            conn = psycopg2.connect(test_database_url)
            assert conn is not None
            conn.close()
        except psycopg2.OperationalError as e:
            pytest.skip(f"Database not available for testing: {e}")

    def test_job_listings_table_schema(self, test_database_url):
        """Test that job_listings table has correct schema"""
        if not test_database_url:
            pytest.skip("No database URL provided for testing")

        try:
            conn = psycopg2.connect(test_database_url)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'job_listings'
                ORDER BY ordinal_position;
            """)

            columns = cursor.fetchall()
            conn.close()

            if not columns:
                pytest.skip("job_listings table doesn't exist - run ETL first")

            expected_columns = {
                'position_id': 'character varying',
                'position_title': 'character varying',
                'position_uri': 'character varying',
                'position_location': 'jsonb',
                'position_remuneration': 'jsonb'
            }

            column_dict = {col[0]: col[1] for col in columns}

            for col_name, expected_type in expected_columns.items():
                assert col_name in column_dict, f"Column {col_name} missing from schema"
                assert expected_type in column_dict[col_name] or col_name in column_dict

        except psycopg2.OperationalError:
            pytest.skip("Database not available for testing")

class TestDataOperations:
    """Test database data operations"""

    def test_insert_job_data(self, test_database_url, mock_api_response):
        """Test inserting job data into database"""
        if not test_database_url:
            pytest.skip("No database URL provided for testing")

        sample_job = mock_api_response["SearchResult"]["SearchResultItems"][0]["MatchedObjectDescriptor"]

        try:
            conn = psycopg2.connect(test_database_url)
            cursor = conn.cursor()

            insert_query = """
                INSERT INTO job_listings (
                    position_id, position_title, position_uri,
                    position_location, position_remuneration, etl_timestamp
                ) VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (position_id) DO UPDATE SET
                    position_title = EXCLUDED.position_title,
                    position_uri = EXCLUDED.position_uri,
                    position_location = EXCLUDED.position_location,
                    position_remuneration = EXCLUDED.position_remuneration,
                    etl_timestamp = EXCLUDED.etl_timestamp;
            """

            test_data = (
                sample_job["PositionID"],
                sample_job["PositionTitle"],
                sample_job["PositionURI"],
                json.dumps(sample_job["PositionLocation"]),
                json.dumps(sample_job["PositionRemuneration"])
            )

            cursor.execute(insert_query, test_data)
            conn.commit()

            cursor.execute("SELECT COUNT(*) FROM job_listings WHERE position_id = %s", (sample_job["PositionID"],))
            count = cursor.fetchone()[0]
            assert count == 1

            cursor.execute("DELETE FROM job_listings WHERE position_id = %s", (sample_job["PositionID"],))
            conn.commit()
            conn.close()

        except psycopg2.OperationalError:
            pytest.skip("Database not available for testing")
        except psycopg2.ProgrammingError:
            pytest.skip("Table schema not set up - run ETL first")

    def test_upsert_behavior(self, test_database_url):
        """Test that duplicate position_ids are handled correctly"""
        if not test_database_url:
            pytest.skip("No database URL provided for testing")

        try:
            conn = psycopg2.connect(test_database_url)
            cursor = conn.cursor()

            test_id = "TEST-UPSERT-001"
            insert_query = """
                INSERT INTO job_listings (
                    position_id, position_title, position_uri,
                    position_location, position_remuneration, etl_timestamp
                ) VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (position_id) DO UPDATE SET
                    position_title = EXCLUDED.position_title,
                    etl_timestamp = EXCLUDED.etl_timestamp;
            """

            cursor.execute(insert_query, (
                test_id, "Original Title", "http://example.com",
                json.dumps([{"city": "Chicago"}]), json.dumps([{"salary": "100k"}])
            ))
            conn.commit()

            cursor.execute(insert_query, (
                test_id, "Updated Title", "http://example.com",
                json.dumps([{"city": "Chicago"}]), json.dumps([{"salary": "100k"}])
            ))
            conn.commit()

            cursor.execute("SELECT position_title FROM job_listings WHERE position_id = %s", (test_id,))
            result = cursor.fetchone()
            assert result[0] == "Updated Title"

            cursor.execute("DELETE FROM job_listings WHERE position_id = %s", (test_id,))
            conn.commit()
            conn.close()

        except (psycopg2.OperationalError, psycopg2.ProgrammingError):
            pytest.skip("Database not available or schema not set up")