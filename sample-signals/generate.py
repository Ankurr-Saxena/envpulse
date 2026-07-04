"""
EnvPulse Sample Signals Generator
=================================
Generates sample probe signals for testing and demos
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any


def generate_sample_signals(count: int = 100, environment: str = 'dev') -> List[Dict[str, Any]]:
    """
    Generate sample probe signals.

    Args:
        count: Number of signals to generate
        environment: Environment name

    Returns:
        List of signal dictionaries
    """
    services = ['api', 'ui', 'database', 'cache', 'storage']
    signal_types = ['api', 'ui', 'health', 'data']
    statuses = ['PASS', 'PASS', 'PASS', 'PASS', 'FAIL', 'TIMEOUT']  # 80% pass rate

    signals = []
    now = datetime.utcnow()

    for i in range(count):
        # Random time within last 24 hours
        time_offset = random.randint(0, 86400)
        timestamp = now - timedelta(seconds=time_offset)

        status = random.choice(statuses)
        response_time = random.randint(100, 5000)

        if status == 'TIMEOUT':
            response_time = random.randint(10000, 30000)

        signal = {
            'probe_id': f'probe-{random.randint(1, 20)}',
            'probe_name': f'Test Probe {random.randint(1, 20)}',
            'environment': environment,
            'service': random.choice(services),
            'signal_type': random.choice(signal_types),
            'status': status,
            'url': f'https://api-{environment}.example.com/test',
            'method': random.choice(['GET', 'POST']),
            'status_code': 200 if status == 'PASS' else 500,
            'response_time_ms': response_time,
            'error_message': 'Request timeout' if status == 'TIMEOUT' else None,
            'validation_passed': status == 'PASS',
            'timestamp': timestamp.isoformat() + 'Z',
            'execution_id': f'exec-{random.randint(1000, 9999)}',
        }
        signals.append(signal)

    return signals


def save_signals(signals: List[Dict], filename: str = 'signals.json'):
    """Save signals to JSON file"""
    with open(filename, 'w') as f:
        json.dump(signals, f, indent=2)
    print(f"Saved {len(signals)} signals to {filename}")


def main():
    """Generate sample signals"""
    print("Generating sample EnvPulse signals...")

    # Generate signals for each environment
    for env in ['dev', 'staging', 'prod']:
        signals = generate_sample_signals(100, env)
        filename = f'signals-{env}.json'
        save_signals(signals, filename)

    # Generate combined signals
    all_signals = []
    for env in ['dev', 'staging', 'prod']:
        all_signals.extend(generate_sample_signals(50, env))

    save_signals(all_signals, 'signals.json')
    print("✓ Sample signals generated successfully!")


if __name__ == '__main__':
    main()
