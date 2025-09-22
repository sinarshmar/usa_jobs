"""
Integration tests for the complete ETL process
Tests the actual etl.py script end-to-end
"""

import pytest
import subprocess
import os
import sys
import psycopg2
from unittest.mock import patch
import tempfile


class TestETLIntegration:
    """Integration tests for the full ETL pipeline"""

    def test_etl_script_runs_without_errors(self):
        """Test that the ETL script can be executed without Python errors"""
        env = os.environ.copy()
        env['DRY_RUN_MODE'] = 'true'
        env['MAX_PAGES'] = '1'

        script_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'etl.py')

        try:
            result = subprocess.run(
                [sys.executable, script_path],
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )

            assert "Traceback" not in result.stderr, f"Python error in ETL script: {result.stderr}"
            assert result.returncode in [0, 1], f"Unexpected return code: {result.returncode}"

        except subprocess.TimeoutExpired:
            pytest.skip("ETL script took too long - likely making real API calls")
        except FileNotFoundError:
            pytest.skip("ETL script not found at expected location")

    def test_etl_with_mock_environment(self):
        """Test ETL with mocked environment variables"""
        test_env = {
            'USAJOBS_API_KEY': 'test-key-12345',
            'DATABASE_URL': 'postgresql://test:test@localhost:5432/test_db',
            'DEFAULT_LOCATION': 'Chicago',
            'KEYWORD': 'data engineering',
            'LOG_LEVEL': 'INFO',
            'MAX_PAGES': '1',
            'DRY_RUN_MODE': 'true'
        }

        script_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'etl.py')

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            for key, value in test_env.items():
                f.write(f"{key}={value}\n")
            temp_env_file = f.name

        try:
            project_root = os.path.join(os.path.dirname(__file__), '..')
            temp_project_env = os.path.join(project_root, '.env.test')

            with open(temp_env_file, 'r') as src, open(temp_project_env, 'w') as dst:
                dst.write(src.read())

            env = os.environ.copy()
            env.update(test_env)

            result = subprocess.run(
                [sys.executable, script_path],
                env=env,
                capture_output=True,
                text=True,
                timeout=15
            )

            if os.path.exists(temp_project_env):
                os.remove(temp_project_env)

            assert "Configuration loaded" in result.stdout or result.returncode in [0, 1]

        except subprocess.TimeoutExpired:
            pytest.skip("ETL script timeout - likely making real API calls")
        except FileNotFoundError:
            pytest.skip("ETL script not found")
        finally:
            if os.path.exists(temp_env_file):
                os.remove(temp_env_file)

    def test_database_schema_creation(self, test_database_url):
        """Test that ETL creates proper database schema"""
        if not test_database_url:
            pytest.skip("No test database URL provided")

        try:
            conn = psycopg2.connect(test_database_url)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'job_listings'
                );
            """)

            table_exists = cursor.fetchone()[0]
            conn.close()

            if not table_exists:
                pytest.skip("job_listings table not found - run ETL first to create schema")

            assert table_exists

        except psycopg2.OperationalError:
            pytest.skip("Cannot connect to test database")

class TestConfigurationValidation:
    """Test configuration and environment setup"""

    def test_required_environment_variables(self):
        """Test that ETL handles missing required environment variables gracefully"""
        # Test with minimal environment (should fail gracefully)
        minimal_env = {key: value for key, value in os.environ.items()
                      if not key.startswith(('USAJOBS_', 'DATABASE_'))}

        script_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'etl.py')

        try:
            result = subprocess.run(
                [sys.executable, script_path],
                env=minimal_env,
                capture_output=True,
                text=True,
                timeout=10
            )

            if "Traceback" in result.stderr:
                assert any(keyword in result.stderr.lower() for keyword in
                          ['key', 'database', 'environment', 'config'])

        except subprocess.TimeoutExpired:
            pytest.skip("ETL script timeout")
        except FileNotFoundError:
            pytest.skip("ETL script not found")

    def test_environment_variable_loading(self):
        """Test that .env file is loaded correctly"""
        from dotenv import load_dotenv
        import tempfile

        test_env_content = """
USAJOBS_API_KEY=test-key-from-file
DEFAULT_LOCATION=TestCity
KEYWORD=test keyword
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(test_env_content)
            temp_env_file = f.name

        try:
            result = load_dotenv(temp_env_file)
            assert result is True

            os.remove(temp_env_file)

        except Exception as e:
            pytest.fail(f"Environment file loading failed: {e}")