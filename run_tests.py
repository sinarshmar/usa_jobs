#!/usr/bin/env python3
"""
Simple test runner for USAJobs ETL
Runs the test suite and provides clear output
"""

import subprocess
import sys
import os

def main():
    print("🧪 Running USAJobs ETL Test Suite")
    print("=" * 40)

    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("❌ pytest not installed. Installing...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pytest', 'pytest-mock'])

    # Run tests
    test_args = [
        '-v',                    # Verbose output
        '--tb=short',           # Short traceback format
        'tests/',               # Test directory
        '-x',                   # Stop on first failure
    ]

    # Add database URL to environment if available
    env = os.environ.copy()
    if 'DATABASE_URL' not in env:
        # Use docker-compose database URL as default for testing
        env['DATABASE_URL'] = 'postgresql://postgres:password@localhost:5432/usa_jobs'

    try:
        result = subprocess.run([sys.executable, '-m', 'pytest'] + test_args,
                              env=env, check=False)

        if result.returncode == 0:
            print("\n✅ All tests passed!")
        else:
            print(f"\n❌ Tests failed with return code {result.returncode}")
            print("💡 Make sure database is running: docker-compose up -d")

        return result.returncode

    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1

if __name__ == '__main__':
    exit(main())