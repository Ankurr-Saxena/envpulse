"""
EnvPulse CLI Utilities
======================
Helper utilities for EnvPulse operations
"""

import argparse
import json
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Any


def run_command(cmd: List[str]) -> Dict[str, Any]:
    """Execute AWS CLI command and return JSON result"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout) if result.stdout else {}
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return {}
    except json.JSONDecodeError:
        print("Error parsing command output")
        return {}


def check_lambda_status(function_name: str = 'envpulse-monitor') -> bool:
    """Check if Lambda function is healthy"""
    cmd = [
        'aws', 'cloudwatch', 'get-metric-statistics',
        '--namespace', 'AWS/Lambda',
        '--metric-name', 'Errors',
        '--dimensions', f'Name=FunctionName,Value={function_name}',
        '--start-time', (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        '--end-time', datetime.utcnow().isoformat(),
        '--period', '300',
        '--statistics', 'Sum',
    ]
    
    result = run_command(cmd)
    errors = sum(dp.get('Sum', 0) for dp in result.get('Datapoints', []))
    
    print(f"Lambda {function_name}:")
    print(f"  Errors (1h): {errors}")
    print(f"  Status: {'✓ Healthy' if errors == 0 else '✗ Unhealthy'}")
    
    return errors == 0


def check_athena_status(database: str = 'envpulse_db') -> bool:
    """Check if Athena database is accessible"""
    cmd = [
        'aws', 'athena', 'list-tables',
        '--catalog-name', 'AwsDataCatalog',
        '--database-name', database,
    ]
    
    result = run_command(cmd)
    tables = result.get('TableList', [])
    
    print(f"Athena Database {database}:")
    print(f"  Tables found: {len(tables)}")
    for table in tables:
        print(f"    - {table['Name']}")
    
    return len(tables) > 0


def check_s3_buckets(pattern: str = 'envpulse') -> bool:
    """List S3 buckets matching pattern"""
    cmd = ['aws', 's3', 'ls']
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    matching_buckets = [
        line.split()[-1] for line in result.stdout.strip().split('\n')
        if pattern in line
    ]
    
    print(f"S3 Buckets matching '{pattern}':")
    if matching_buckets:
        for bucket in matching_buckets:
            print(f"  - s3://{bucket}")
    else:
        print("  No buckets found")
    
    return len(matching_buckets) > 0


def health_check():
    """Run full health check"""
    print("=" * 60)
    print("EnvPulse Health Check")
    print("=" * 60)
    print()
    
    checks = [
        ("Lambda", lambda: check_lambda_status()),
        ("Athena", lambda: check_athena_status()),
        ("S3 Buckets", lambda: check_s3_buckets()),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"{name}: ✗ Error - {str(e)}")
            results.append((name, False))
        print()
    
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    print(f"Summary: {passed}/{len(results)} checks passed")
    print("=" * 60)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='EnvPulse CLI Utilities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python utils.py health-check
  python utils.py lambda-status
  python utils.py athena-status
  python utils.py s3-check
        """,
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Health check command
    subparsers.add_parser('health-check', help='Run full health check')
    
    # Lambda status command
    lambda_parser = subparsers.add_parser('lambda-status', help='Check Lambda status')
    lambda_parser.add_argument(
        '--function-name',
        default='envpulse-monitor',
        help='Lambda function name'
    )
    
    # Athena status command
    athena_parser = subparsers.add_parser('athena-status', help='Check Athena status')
    athena_parser.add_argument(
        '--database',
        default='envpulse_db',
        help='Athena database name'
    )
    
    # S3 check command
    s3_parser = subparsers.add_parser('s3-check', help='Check S3 buckets')
    s3_parser.add_argument(
        '--pattern',
        default='envpulse',
        help='Bucket name pattern'
    )
    
    args = parser.parse_args()
    
    if args.command == 'health-check':
        health_check()
    elif args.command == 'lambda-status':
        check_lambda_status(args.function_name)
    elif args.command == 'athena-status':
        check_athena_status(args.database)
    elif args.command == 's3-check':
        check_s3_buckets(args.pattern)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
