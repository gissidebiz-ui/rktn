"""
Unit tests for config_loader module.
Tests YAML loading functionality and path resolution.
"""
import unittest
import sys
import os
from unittest.mock import patch, mock_open

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config_loader import load_yaml, _get_config_path


class TestConfigLoader(unittest.TestCase):
    """Test suite for config_loader module."""

    def test_get_config_path_returns_absolute_path(self):
        """Test that _get_config_path returns absolute path with correct filename."""
        result = _get_config_path("test_file.yaml")
        self.assertTrue(os.path.isabs(result))
        self.assertTrue(result.endswith("config/test_file.yaml"))

    def test_get_config_path_with_different_filenames(self):
        """Test _get_config_path with various file names."""
        test_files = ["secrets.yaml", "themes.yaml", "accounts.yaml", "generation_policy.yaml"]
        for filename in test_files:
            result = _get_config_path(filename)
            self.assertTrue(result.endswith(f"config/{filename}"))

    def test_load_yaml_with_valid_content(self):
        """Test load_yaml with mocked YAML content."""
        yaml_content = "test_key: test_value\nlist_key:\n  - item1\n  - item2"
        
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = load_yaml("dummy_path.yaml")
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get("test_key"), "test_value")
            self.assertEqual(result.get("list_key"), ["item1", "item2"])

    def test_load_yaml_with_empty_file(self):
        """Test load_yaml with empty YAML file."""
        with patch("builtins.open", mock_open(read_data="")):
            result = load_yaml("empty.yaml")
            self.assertIsNone(result)

    def test_load_yaml_file_not_found(self):
        """Test load_yaml raises FileNotFoundError for missing files."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with self.assertRaises(FileNotFoundError):
                load_yaml("nonexistent.yaml")

    def test_get_config_path_no_traversal(self):
        """Test that config path cannot traverse to parent directories."""
        result = _get_config_path("secrets.yaml")
        # Should end with config/secrets.yaml, not ../../../anywhere
        self.assertNotIn("..", result)
        self.assertTrue("config" in result)


class TestConfigLoaderIntegration(unittest.TestCase):
    """Integration tests with actual config files."""

    def setUp(self):
        """Setup test environment."""
        self.test_dir = os.path.dirname(__file__)
        self.rktn_dir = os.path.dirname(self.test_dir)

    def test_load_generation_policy_structure(self):
        """Test that generation_policy.yaml has expected structure."""
        from config_loader import load_generation_policy
        config = load_generation_policy()
        
        self.assertIsInstance(config, dict)
        expected_keys = [
            "normal_post_generation",
            "affiliate_post_generation",
            "ai_generation",
            "html_cleanup",
            "api"
        ]
        for key in expected_keys:
            self.assertIn(key, config, f"Missing key: {key}")

    def test_load_secrets_contains_required_keys(self):
        """Test that secrets.yaml contains required API keys."""
        from config_loader import load_secrets
        secrets = load_secrets()
        
        self.assertIsInstance(secrets, dict)
        self.assertIn("google_api_key", secrets)
        self.assertIn("base_url", secrets)

    def test_load_accounts_returns_account_list(self):
        """Test that accounts.yaml is loaded correctly."""
        from config_loader import load_accounts
        accounts = load_accounts()
        
        self.assertIsInstance(accounts, list)
        # Should have at least one account
        self.assertGreater(len(accounts), 0)
        # Each account should have required fields
        for account in accounts:
            self.assertIn("name", account)
            self.assertIn("themes", account)

    def test_load_themes_returns_theme_dict(self):
        """Test that themes.yaml is loaded correctly."""
        from config_loader import load_themes
        themes = load_themes()
        
        self.assertIsInstance(themes, dict)
        # Should have at least one theme
        self.assertGreater(len(themes), 0)


if __name__ == "__main__":
    unittest.main()
