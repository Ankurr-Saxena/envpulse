"""
EnvPulse UI Probe Runner
=======================
Executes browser-based synthetic tests using Playwright and uploads results to S3.

Features:
- Multi-browser support (Chromium, Firefox, WebKit)
- Headless and headed modes
- Screenshot capture on failure
- Performance metrics collection
- Custom actions (navigate, fill, click, wait, etc.)
- Error handling with screenshots
- S3 result storage
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

import yaml
import boto3
from botocore.exceptions import BotoCoreError, ClientError

try:
    from playwright.sync_api import (
        sync_playwright,
        Page,
        Browser,
        BrowserContext,
        TimeoutError as PlaywrightTimeoutError,
    )
except ImportError:
    print("Playwright not installed. Install with: pip install playwright")
    print("Then run: playwright install")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class UIProbeStatus(Enum):
    """UI probe execution status"""
    PASS = "PASS"
    FAIL = "FAIL"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


@dataclass
class UIProbeResult:
    """Result from a UI probe execution"""
    probe_id: str
    probe_name: str
    environment: str
    service: str
    signal_type: str
    status: str
    url: str
    test_name: str
    response_time_ms: int = 0
    steps_completed: int = 0
    total_steps: int = 0
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    validation_passed: bool = True
    timestamp: str = ""
    execution_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for S3 storage"""
        return asdict(self)


class UITest:
    """Browser-based UI test execution"""

    def __init__(
        self, 
        test_config: Dict[str, Any], 
        execution_id: str,
        browser: Browser,
        screenshot_dir: str,
    ):
        """
        Initialize UI test.

        Args:
            test_config: Test configuration
            execution_id: Unique execution ID
            browser: Playwright browser instance
            screenshot_dir: Directory for saving screenshots
        """
        self.probe_id = test_config.get('id', 'unknown-ui-test')
        self.probe_name = test_config.get('name', self.probe_id)
        self.environment = test_config.get('environment', 'dev')
        self.service = test_config.get('service', 'ui')
        self.url = test_config.get('url')
        self.test_name = test_config.get('test_name', 'default-test')
        self.steps = test_config.get('steps', [])
        self.timeout_seconds = test_config.get('timeout_seconds', 30)
        self.viewport = test_config.get('viewport', {'width': 1280, 'height': 720})
        self.execution_id = execution_id
        self.browser = browser
        self.screenshot_dir = screenshot_dir

        if not self.url:
            raise ValueError(f"Test {self.probe_id}: URL is required")

        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)

    def _take_screenshot(self, page: Page, label: str) -> Optional[str]:
        """Take a screenshot and save it"""
        try:
            filename = (
                f"{self.probe_id}_{label}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            )
            filepath = os.path.join(self.screenshot_dir, filename)
            page.screenshot(path=filepath)
            logger.debug(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            logger.warning(f"Failed to capture screenshot: {str(e)}")
            return None

    def _execute_step(self, page: Page, step: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Execute a single test step.

        Returns:
            Tuple of (success, error_message)
        """
        action = step.get('action', '').lower()
        
        try:
            if action == 'navigate':
                url = step.get('url', self.url)
                logger.debug(f"Navigating to: {url}")
                page.goto(url, wait_until='networkidle')
                return True, ""

            elif action == 'fill':
                selector = step.get('selector')
                value = step.get('value')
                logger.debug(f"Filling {selector} with '{value}'")
                page.fill(selector, value)
                return True, ""

            elif action == 'click':
                selector = step.get('selector')
                logger.debug(f"Clicking {selector}")
                page.click(selector)
                return True, ""

            elif action == 'wait':
                selector = step.get('selector')
                timeout_ms = step.get('timeout_ms', self.timeout_seconds * 1000)
                logger.debug(f"Waiting for {selector} (timeout: {timeout_ms}ms)")
                page.wait_for_selector(selector, timeout=timeout_ms)
                return True, ""

            elif action == 'wait_for_navigation':
                timeout_ms = step.get('timeout_ms', self.timeout_seconds * 1000)
                logger.debug(f"Waiting for navigation (timeout: {timeout_ms}ms)")
                with page.expect_navigation(timeout=timeout_ms):
                    pass
                return True, ""

            elif action == 'type':
                selector = step.get('selector')
                text = step.get('text')
                delay = step.get('delay_ms', 0)
                logger.debug(f"Typing into {selector}")
                page.locator(selector).type(text, delay=delay)
                return True, ""

            elif action == 'check':
                selector = step.get('selector')
                logger.debug(f"Checking {selector}")
                page.check(selector)
                return True, ""

            elif action == 'select':
                selector = step.get('selector')
                value = step.get('value')
                logger.debug(f"Selecting {value} in {selector}")
                page.select_option(selector, value)
                return True, ""

            elif action == 'screenshot':
                label = step.get('label', 'step')
                self._take_screenshot(page, label)
                return True, ""

            elif action == 'assert_text':
                selector = step.get('selector')
                expected_text = step.get('text')
                actual_text = page.text_content(selector)
                if expected_text in actual_text:
                    logger.debug(f"Text assertion passed: {selector}")
                    return True, ""
                else:
                    return False, f"Expected '{expected_text}' in '{actual_text}'"

            elif action == 'assert_visible':
                selector = step.get('selector')
                is_visible = page.is_visible(selector)
                if is_visible:
                    logger.debug(f"Visibility assertion passed: {selector}")
                    return True, ""
                else:
                    return False, f"Element not visible: {selector}"

            else:
                return False, f"Unknown action: {action}"

        except PlaywrightTimeoutError as e:
            return False, f"Timeout: {str(e)}"
        except Exception as e:
            return False, f"{action} failed: {str(e)}"

    def run(self) -> UIProbeResult:
        """Execute the UI test"""
        result = UIProbeResult(
            probe_id=self.probe_id,
            probe_name=self.probe_name,
            environment=self.environment,
            service=self.service,
            signal_type='ui',
            status=UIProbeStatus.ERROR.value,
            url=self.url,
            test_name=self.test_name,
            total_steps=len(self.steps),
            timestamp=datetime.utcnow().isoformat() + 'Z',
            execution_id=self.execution_id,
        )

        start_time = time.time()
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None

        try:
            # Create browser context and page
            context = self.browser.new_context(viewport=self.viewport)
            page = context.new_page()

            # Execute test steps
            for i, step in enumerate(self.steps, start=1):
                success, error = self._execute_step(page, step)
                result.steps_completed = i

                if not success:
                    result.status = UIProbeStatus.FAIL.value
                    result.error_message = error
                    result.validation_passed = False
                    result.screenshot_path = self._take_screenshot(page, "failure")
                    logger.warning(f"✗ {self.probe_id}: FAIL at step {i} - {error}")
                    break

            # If all steps passed
            if result.steps_completed == len(self.steps):
                result.status = UIProbeStatus.PASS.value
                result.validation_passed = True
                logger.info(
                    f"✓ {self.probe_id}: PASS ({result.steps_completed} steps)"
                )

        except PlaywrightTimeoutError as e:
            result.status = UIProbeStatus.TIMEOUT.value
            result.error_message = f"Test timeout: {str(e)}"
            if page:
                result.screenshot_path = self._take_screenshot(page, "timeout")
            logger.error(f"✗ {self.probe_id}: TIMEOUT - {str(e)}")

        except Exception as e:
            result.status = UIProbeStatus.ERROR.value
            result.error_message = f"Test error: {str(e)}"
            if page:
                result.screenshot_path = self._take_screenshot(page, "error")
            logger.exception(f"✗ {self.probe_id}: ERROR - {str(e)}")

        finally:
            elapsed = time.time() - start_time
            result.response_time_ms = int(elapsed * 1000)

            if page:
                page.close()
            if context:
                context.close()

        return result


class UIProbeRunner:
    """Runs multiple UI probes and stores results"""

    def __init__(self, config_file: str, environment: str, browser_type: str = 'chromium'):
        """
        Initialize UI probe runner.

        Args:
            config_file: Path to tests configuration YAML
            environment: Environment name
            browser_type: Browser type (chromium, firefox, webkit)
        """
        self.config_file = config_file
        self.environment = environment
        self.browser_type = browser_type
        self.execution_id = (
            f"exec-ui-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        )
        self.screenshot_dir = f"screenshots/{self.execution_id}"
        self.s3_client = boto3.client('s3')
        self.results: List[UIProbeResult] = []
        self.playwright = None
        self.browser = None

        logger.info(f"Initialized UIProbeRunner for environment: {environment}")
        logger.info(f"Browser: {browser_type}")
        logger.info(f"Execution ID: {self.execution_id}")

    def load_config(self) -> List[Dict[str, Any]]:
        """Load test configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                tests = config.get('tests', [])

                # Filter by environment
                filtered = [
                    t for t in tests if t.get('environment') == self.environment
                ]

                logger.info(f"Loaded {len(filtered)} tests for {self.environment}")
                return filtered

        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_file}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML config: {str(e)}")
            raise

    def setup(self):
        """Set up browser instance"""
        self.playwright = sync_playwright().start()

        if self.browser_type == 'chromium':
            self.browser = self.playwright.chromium.launch(headless=True)
        elif self.browser_type == 'firefox':
            self.browser = self.playwright.firefox.launch(headless=True)
        elif self.browser_type == 'webkit':
            self.browser = self.playwright.webkit.launch(headless=True)
        else:
            raise ValueError(f"Unknown browser type: {self.browser_type}")

        logger.info(f"Browser launched: {self.browser_type}")

    def teardown(self):
        """Clean up browser instance"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser closed")

    def run_tests(self) -> List[UIProbeResult]:
        """Execute all configured tests"""
        config = self.load_config()
        logger.info(f"Running {len(config)} UI tests...")

        for test_config in config:
            try:
                test = UITest(test_config, self.execution_id, self.browser, self.screenshot_dir)
                result = test.run()
                self.results.append(result)
            except Exception as e:
                logger.error(f"Failed to run test: {str(e)}")

        logger.info(f"Completed {len(self.results)} UI tests")
        return self.results

    def upload_results(self, s3_bucket: str) -> bool:
        """
        Upload results to S3.

        Args:
            s3_bucket: S3 bucket name

        Returns:
            True if successful
        """
        if not self.results:
            logger.warning("No results to upload")
            return True

        today = datetime.utcnow()
        s3_key = (
            f"signals/year={today.year}/month={today.month}/day={today.day}/"
            f"ui-tests-{self.execution_id}.json"
        )

        data = {
            'execution_id': self.execution_id,
            'environment': self.environment,
            'browser': self.browser_type,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'test_count': len(self.results),
            'signals': [r.to_dict() for r in self.results],
        }

        try:
            self.s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=json.dumps(data, indent=2),
                ContentType='application/json',
            )
            logger.info(f"Uploaded results to s3://{s3_bucket}/{s3_key}")
            return True

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to upload to S3: {str(e)}")
            return False

    def print_summary(self):
        """Print execution summary"""
        if not self.results:
            return

        passed = sum(1 for r in self.results if r.status == UIProbeStatus.PASS.value)
        failed = sum(1 for r in self.results if r.status == UIProbeStatus.FAIL.value)
        errors = sum(1 for r in self.results if r.status == UIProbeStatus.ERROR.value)
        timeouts = sum(1 for r in self.results if r.status == UIProbeStatus.TIMEOUT.value)

        print("\n" + "=" * 60)
        print(f"EnvPulse UI Probe Summary")
        print("=" * 60)
        print(f"Execution ID: {self.execution_id}")
        print(f"Environment: {self.environment}")
        print(f"Browser: {self.browser_type}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
        print("-" * 60)
        print(f"Total Tests:   {len(self.results)}")
        print(f"✓ Passed:      {passed}")
        print(f"✗ Failed:      {failed}")
        print(f"⚠ Errors:      {errors}")
        print(f"⏱ Timeouts:    {timeouts}")

        if self.results:
            avg_time = sum(r.response_time_ms for r in self.results) / len(self.results)
            max_time = max(r.response_time_ms for r in self.results)
            min_time = min(r.response_time_ms for r in self.results)
            print("-" * 60)
            print(f"Execution Time: avg={avg_time:.0f}ms, min={min_time}ms, max={max_time}ms")

        print(f"Screenshots: {self.screenshot_dir}")
        print("=" * 60 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='EnvPulse UI Probe Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python runner.py --config config/ui-tests.yaml --environment prod
  python runner.py -c config/ui-tests.yaml -e staging --s3-bucket my-signals --browser firefox
        """,
    )

    parser.add_argument(
        '-c', '--config',
        default='config/ui-tests.yaml',
        help='Path to tests configuration file (default: config/ui-tests.yaml)',
    )
    parser.add_argument(
        '-e', '--environment',
        required=True,
        help='Environment name (dev, staging, prod, etc.)',
    )
    parser.add_argument(
        '-b', '--browser',
        choices=['chromium', 'firefox', 'webkit'],
        default='chromium',
        help='Browser type (default: chromium)',
    )
    parser.add_argument(
        '-s', '--s3-bucket',
        help='S3 bucket for uploading results (optional)',
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging',
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    runner = UIProbeRunner(args.config, args.environment, args.browser)

    try:
        runner.setup()
        results = runner.run_tests()
        runner.print_summary()

        if args.s3_bucket:
            runner.upload_results(args.s3_bucket)

    except KeyboardInterrupt:
        logger.info("UI probe runner interrupted by user")
    except Exception as e:
        logger.exception(f"UI probe runner failed: {str(e)}")
        sys.exit(1)
    finally:
        runner.teardown()


if __name__ == '__main__':
    main()
