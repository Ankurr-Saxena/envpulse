#!/usr/bin/env python
"""
EnvPulse Local Test Runner
==========================
Run probes locally with sample configuration
"""

import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from api_probes.runner import ProbeRunner as APIProbeRunner


def run_api_probes():
    """Run API probes with test configuration"""
    print("Running EnvPulse API probes locally...")
    
    runner = APIProbeRunner('config/probes.yaml', 'development')
    results = runner.run_probes()
    runner.print_summary()
    
    return len([r for r in results if r.status == 'PASS'])


if __name__ == '__main__':
    try:
        run_api_probes()
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
