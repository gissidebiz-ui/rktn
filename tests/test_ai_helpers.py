"""
Unit tests for ai_helpers module.
Tests AI client creation and generation with mocks.
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock, Mock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai_helpers import create_ai_client, generate_with_retry


class TestCreateAiClient(unittest.TestCase):
    """Test suite for create_ai_client function."""

    @patch('google.genai.Client')
    def test_creates_genai_client(self, mock_genai_client):
        """Test that create_ai_client creates a genai.Client."""
        test_api_key = "test_api_key_12345"
        
        client = create_ai_client(test_api_key)
        
        # genai.Client should be called with the API key
        mock_genai_client.assert_called_once_with(api_key=test_api_key)

    @patch('google.genai.Client')
    def test_returns_client_instance(self, mock_genai_client):
        """Test that create_ai_client returns a client instance."""
        mock_instance = Mock()
        mock_genai_client.return_value = mock_instance
        
        client = create_ai_client("test_key")
        
        self.assertEqual(client, mock_instance)


class TestGenerateWithRetry(unittest.TestCase):
    """Test suite for generate_with_retry function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.test_prompt = "Test prompt for AI"
        self.test_config = {
            "max_retries": 3,
            "base": 2.0,
            "max_backoff": 60,
            "rate_limit_multiplier": 6
        }

    def test_successful_generation_on_first_attempt(self):
        """Test successful text generation on first attempt."""
        expected_response = "This is the AI response"
        
        mock_response = Mock()
        mock_response.text = expected_response
        self.mock_client.models.generate_content.return_value = mock_response
        
        result = generate_with_retry(self.mock_client, self.test_prompt, self.test_config)
        
        self.assertEqual(result, expected_response)
        # Should only call API once
        self.mock_client.models.generate_content.assert_called_once()

    def test_retries_on_failure_then_succeeds(self):
        """Test that function retries after failure."""
        expected_response = "Success after retry"
        
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.text = expected_response
        
        self.mock_client.models.generate_content.side_effect = [
            Exception("Rate limit exceeded"),
            mock_response
        ]
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = generate_with_retry(self.mock_client, self.test_prompt, self.test_config)
        
        self.assertEqual(result, expected_response)
        # Should call API twice
        self.assertEqual(self.mock_client.models.generate_content.call_count, 2)

    def test_returns_empty_on_max_retries_exceeded(self):
        """Test that function returns empty string after max retries."""
        self.mock_client.models.generate_content.side_effect = Exception("Persistent error")
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = generate_with_retry(self.mock_client, self.test_prompt, self.test_config)
        
        self.assertEqual(result, "")
        # Should call API max_retries times
        self.assertEqual(self.mock_client.models.generate_content.call_count, 3)

    def test_handles_response_without_text_attribute(self):
        """Test handling of responses with alternative structure."""
        expected_text = "Response from candidates"
        
        mock_response = Mock(spec=[])  # No 'text' attribute
        mock_response.candidates = [
            Mock(content=Mock(parts=[Mock(text=expected_text)]))
        ]
        self.mock_client.models.generate_content.return_value = mock_response
        
        result = generate_with_retry(self.mock_client, self.test_prompt, self.test_config)
        
        self.assertEqual(result, expected_text)

    @patch('retry_helper.metrics_log')
    def test_logs_metrics_on_success(self, mock_metrics_log):
        """Test that metrics are logged on successful generation."""
        mock_response = Mock()
        mock_response.text = "Test response"
        self.mock_client.models.generate_content.return_value = mock_response
        
        result = generate_with_retry(self.mock_client, self.test_prompt, self.test_config)
        
        # Should log success metrics
        self.assertTrue(mock_metrics_log.called)

    @patch('retry_helper.metrics_log')
    def test_logs_metrics_on_error(self, mock_metrics_log):
        """Test that metrics are logged on error."""
        self.mock_client.models.generate_content.side_effect = Exception("Test error")
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = generate_with_retry(self.mock_client, self.test_prompt, self.test_config)
        
        # Should log error metrics
        self.assertTrue(mock_metrics_log.called)

    def test_strips_whitespace_from_response(self):
        """Test that response whitespace is stripped."""
        response_with_whitespace = "   Response with whitespace   \n\n"
        
        mock_response = Mock()
        mock_response.text = response_with_whitespace
        self.mock_client.models.generate_content.return_value = mock_response
        
        result = generate_with_retry(self.mock_client, self.test_prompt, self.test_config)
        
        self.assertEqual(result, "Response with whitespace")

    def test_uses_correct_model_name(self):
        """Test that correct model is used for generation."""
        mock_response = Mock()
        mock_response.text = "Response"
        self.mock_client.models.generate_content.return_value = mock_response
        
        generate_with_retry(self.mock_client, self.test_prompt, self.test_config)
        
        # Check that correct model was used
        call_args = self.mock_client.models.generate_content.call_args
        self.assertEqual(call_args.kwargs.get("model", call_args[1].get("model")), "gemini-2.0-flash")

    def test_respects_max_retries_from_config(self):
        """Test that max_retries from config is respected."""
        config_with_custom_retries = {
            "max_retries": 5,
            "base": 2.0,
            "max_backoff": 60,
            "rate_limit_multiplier": 6
        }
        
        self.mock_client.models.generate_content.side_effect = Exception("Error")
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = generate_with_retry(self.mock_client, self.test_prompt, config_with_custom_retries)
        
        # Should call API max_retries times
        self.assertEqual(self.mock_client.models.generate_content.call_count, 5)


class TestGenerateWithRetryEdgeCases(unittest.TestCase):
    """Edge case tests for generate_with_retry."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.test_config = {
            "max_retries": 2,
            "base": 2.0,
            "max_backoff": 60,
            "rate_limit_multiplier": 6
        }

    def test_empty_response_text(self):
        """Test handling of empty response text."""
        mock_response = Mock()
        mock_response.text = ""
        self.mock_client.models.generate_content.return_value = mock_response
        
        result = generate_with_retry(self.mock_client, "prompt", self.test_config)
        
        # Empty response should be returned as is
        self.assertEqual(result, "")

    def test_only_whitespace_response(self):
        """Test handling of response with only whitespace."""
        mock_response = Mock()
        mock_response.text = "   \n\t  "
        self.mock_client.models.generate_content.return_value = mock_response
        
        result = generate_with_retry(self.mock_client, "prompt", self.test_config)
        
        # Should return empty after stripping
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
