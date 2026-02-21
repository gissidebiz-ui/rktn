"""
Simplified unit tests for new modules.
Focus on key functionality with real implementation.
"""
import unittest
import sys
import os
import tempfile
import shutil

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestConfigLoaderIntegration(unittest.TestCase):
    """Integration tests with actual config files."""

    def test_load_generation_policy(self):
        """Test that generation_policy.yaml loads correctly."""
        from config_loader import load_generation_policy
        config = load_generation_policy()
        
        self.assertIsInstance(config, dict)
        self.assertIn("normal_post_generation", config)
        self.assertIn("affiliate_post_generation", config)

    def test_load_secrets(self):
        """Test that secrets.yaml loads correctly."""
        from config_loader import load_secrets
        secrets = load_secrets()
        
        self.assertIsInstance(secrets, dict)
        self.assertIn("google_api_key", secrets)

    def test_load_accounts(self):
        """Test that accounts.yaml loads correctly."""
        from config_loader import load_accounts
        accounts = load_accounts()
        
        self.assertIsInstance(accounts, dict)
        self.assertGreater(len(accounts), 0)

    def test_load_themes(self):
        """Test that themes.yaml loads correctly."""
        from config_loader import load_themes
        themes = load_themes()
        
        self.assertIsInstance(themes, dict)
        self.assertGreater(len(themes), 0)


class TestHtmlGenerator(unittest.TestCase):
    """Test HTML generator functions."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_random_filename_length(self):
        """Test random filename generation."""
        from html_generator import random_filename
        
        filename = random_filename()
        self.assertEqual(len(filename), 6)
        
        filename = random_filename(10)
        self.assertEqual(len(filename), 10)

    def test_create_redirect_html(self):
        """Test HTML file creation."""
        from html_generator import create_redirect_html
        
        create_redirect_html(
            url="https://example.com",
            filename="test",
            title="Test",
            output_dir=self.test_dir
        )
        
        html_file = os.path.join(self.test_dir, "test.html")
        self.assertTrue(os.path.exists(html_file))
        
        with open(html_file, "r") as f:
            content = f.read()
        self.assertIn("example.com", content)
        self.assertIn("<!DOCTYPE html>", content)

    def test_generate_short_url(self):
        """Test short URL generation."""
        from html_generator import generate_short_url
        from unittest.mock import patch
        
        with patch('html_generator.load_secrets') as mock_secrets:
            mock_secrets.return_value = {"base_url": "https://example.com/test"}
            
            url = generate_short_url(
                affiliate_url="https://rakuten.co.jp/item",
                product_name="Test",
                image_url="https://example.com/img.jpg",
                output_dir=self.test_dir
            )
            
            self.assertTrue(url.startswith("https://example.com/test"))
            self.assertTrue(url.endswith(".html"))


class TestRetryHelper(unittest.TestCase):
    """Test retry helper functions."""

    def test_should_retry_on_error(self):
        """Test rate limit detection."""
        from retry_helper import should_retry_on_error
        
        # Should detect rate limit
        self.assertTrue(should_retry_on_error("RESOURCE_EXHAUSTED"))
        self.assertTrue(should_retry_on_error("429 error"))
        self.assertTrue(should_retry_on_error("rate limit"))
        
        # Should not retry on permanent errors
        self.assertFalse(should_retry_on_error("Invalid API key"))

    def test_calculate_backoff(self):
        """Test backoff calculation."""
        from retry_helper import calculate_backoff
        
        config = {
            "retry_base_backoff": 2.0,
            "retry_max_backoff": 120,
            "retry_jitter_max": 2,
            "rate_limit_multiplier": 6
        }
        
        backoff, jitter, total = calculate_backoff(1, False, config)
        
        self.assertGreater(backoff, 0)
        self.assertGreaterEqual(jitter, 0)
        self.assertGreater(total, 0)
        self.assertLessEqual(total, 120 + 2)

    def test_metrics_log(self):
        """Test metrics logging."""
        from retry_helper import metrics_log
        from unittest.mock import patch
        
        # Should not raise exception
        with patch('os.makedirs'):
            with patch('builtins.open'):
                metrics_log("test_event", {"data": "test"})


class TestAiHelpers(unittest.TestCase):
    """Test AI helper functions."""

    def test_create_ai_client(self):
        """Test AI client creation."""
        from ai_helpers import create_ai_client
        from unittest.mock import patch
        
        with patch('google.genai.Client') as mock_client:
            result = create_ai_client("test_key")
            mock_client.assert_called_once_with(api_key="test_key")

    def test_generate_with_retry(self):
        """Test generate with retry."""
        from ai_helpers import generate_with_retry
        from unittest.mock import Mock
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "Test response"
        mock_client.models.generate_content.return_value = mock_response
        
        config = {
            "max_retries": 3,
            "base": 2.0,
            "max_backoff": 60
        }
        
        result = generate_with_retry(mock_client, "prompt", config)
        
        self.assertEqual(result, "Test response")


if __name__ == "__main__":
    unittest.main()
