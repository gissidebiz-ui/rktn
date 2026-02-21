"""
Unit tests for retry_helper module.
Tests retry logic, metrics logging, and backoff calculation.
"""
import unittest
import sys
import os
from unittest.mock import patch

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from retry_helper import (
    metrics_log, should_retry_on_error, calculate_backoff
)


class TestCalculateBackoff(unittest.TestCase):
    """Test suite for calculate_backoff function."""

    def test_backoff_increases_exponentially(self):
        """Test exponential backoff calculation."""
        base = 2.0
        
        # Backoff should increase: 2, 4, 8, 16, 32...
        result1 = calculate_backoff(1, base, 120)
        result2 = calculate_backoff(2, base, 120)
        result3 = calculate_backoff(3, base, 120)
        
        self.assertLess(result1, result2)
        self.assertLess(result2, result3)

    def test_backoff_respects_max_limit(self):
        """Test that backoff respects maximum limit."""
        max_backoff = 120
        
        # Even at high attempts, should not exceed max_backoff
        result = calculate_backoff(10, 2.0, max_backoff)
        self.assertLessEqual(result, max_backoff)

    def test_backoff_rate_limit_multiplier(self):
        """Test backoff with rate limit multiplier."""
        without_multiplier = calculate_backoff(1, 2.0, 120, rate_limit_multiplier=1)
        with_multiplier = calculate_backoff(1, 2.0, 120, rate_limit_multiplier=6)
        
        # With multiplier should be approximately 6x larger
        self.assertAlmostEqual(with_multiplier / without_multiplier, 6, places=0)

    def test_backoff_with_jitter(self):
        """Test backoff calculation returns value within expected range."""
        attempt = 2
        base = 2.0
        max_backoff = 120
        
        # Call multiple times to check variance (jitter)
        results = [calculate_backoff(attempt, base, max_backoff) for _ in range(5)]
        
        # All results should be positive
        self.assertTrue(all(r > 0 for r in results))
        # All results should be less than max
        self.assertTrue(all(r <= max_backoff for r in results))


class TestShouldRetryOnError(unittest.TestCase):
    """Test suite for should_retry_on_error function."""

    def test_rate_limit_error_is_retryable(self):
        """Test various rate limit error messages are recognized."""
        rate_limit_errors = [
            "RESOURCE_EXHAUSTED error",
            "429 Too Many Requests",
            "rate limit exceeded",
            "Rate limit reached"
        ]
        
        for error_msg in rate_limit_errors:
            result = should_retry_on_error(error_msg)
            self.assertTrue(result, f"Should retry on: {error_msg}")

    def test_permanent_error_not_retryable(self):
        """Test that permanent errors are not retried."""
        permanent_errors = [
            "Authentication failed",
            "Invalid API key",
            "Not found",
            "Permission denied"
        ]
        
        for error_msg in permanent_errors:
            result = should_retry_on_error(error_msg)
            self.assertFalse(result, f"Should not retry on: {error_msg}")

    def test_network_error_is_retryable(self):
        """Test that network-related errors are retryable."""
        network_errors = [
            "Connection timeout",
            "ECONNREFUSED",
            "ETIMEDOUT",
            "Connection reset by peer"
        ]
        
        for error_msg in network_errors:
            result = should_retry_on_error(error_msg)
            self.assertTrue(result, f"Should retry on: {error_msg}")


class TestMetricsLog(unittest.TestCase):
    """Test suite for metrics_log function."""

    @patch('os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_metrics_log_writes_json_entry(self, mock_file, mock_makedirs):
        """Test that metrics_log writes valid JSON to file."""
        metrics_log("test_event", {"info": "test_data"})
        
        # Check that file was opened
        mock_file.assert_called()
        
        # Check that data was written
        write_calls = mock_file().write.call_args_list
        self.assertGreater(len(write_calls), 0)
        
        # Check that written data is valid JSON
        written_data = write_calls[0][0][0]
        parsed = json.loads(written_data)
        self.assertEqual(parsed["event"], "test_event")
        self.assertEqual(parsed["info"]["info"], "test_data")
        self.assertIn("timestamp", parsed)

    @patch('os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_metrics_log_with_none_info(self, mock_file, mock_makedirs):
        """Test metrics_log with None info parameter."""
        metrics_log("simple_event", None)
        
        write_calls = mock_file().write.call_args_list
        written_data = write_calls[0][0][0]
        parsed = json.loads(written_data)
        
        self.assertEqual(parsed["event"], "simple_event")
        self.assertEqual(parsed["info"], {})

    @patch('os.makedirs', side_effect=Exception("Write permission denied"))
    def test_metrics_log_handles_write_errors_gracefully(self, mock_makedirs):
        """Test that metrics_log doesn't raise exceptions on write errors."""
        # Should not raise exception even if write fails
        try:
            metrics_log("test_event", {"test": "data"})
        except Exception as e:
            self.fail(f"metrics_log raised exception: {e}")


class TestLogRetryAttempt(unittest.TestCase):
    """Test suite for log_retry_attempt function."""

    @patch('retry_helper.metrics_log')
    def test_log_retry_attempt_calls_metrics_log(self, mock_metrics_log):
        """Test that log_retry_attempt calls metrics_log."""
        log_retry_attempt(
            attempt=1,
            max_retries=3,
            error_message="Test error",
            is_rate_limit=False,
            backoff_seconds=2.0
        )
        
        # Should call metrics_log
        mock_metrics_log.assert_called()

    @patch('retry_helper.metrics_log')
    def test_log_retry_attempt_with_rate_limit(self, mock_metrics_log):
        """Test log_retry_attempt with rate limit flag."""
        log_retry_attempt(
            attempt=2,
            max_retries=8,
            error_message="Rate limit error",
            is_rate_limit=True,
            backoff_seconds=12.0
        )
        
        # Should log the retry attempt
        mock_metrics_log.assert_called()


if __name__ == "__main__":
    unittest.main()
