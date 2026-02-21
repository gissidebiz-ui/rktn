"""
Unit tests for html_generator module.
Tests HTML generation, filename generation, and short URL creation.
"""
import unittest
import sys
import os
import tempfile
import shutil
from unittest.mock import patch, mock_open, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from html_generator import random_filename, create_redirect_html, generate_short_url


class TestRandomFilename(unittest.TestCase):
    """Test suite for random_filename function."""

    def test_default_length_is_six(self):
        """Test that default filename length is 6 characters."""
        filename = random_filename()
        self.assertEqual(len(filename), 6)

    def test_custom_length(self):
        """Test random_filename with custom length."""
        for length in [4, 8, 12, 20]:
            filename = random_filename(length)
            self.assertEqual(len(filename), length)

    def test_filename_contains_only_alphanumeric(self):
        """Test that filename contains only lowercase letters and digits."""
        import string
        valid_chars = set(string.ascii_lowercase + string.digits)
        
        for _ in range(10):
            filename = random_filename()
            for char in filename:
                self.assertIn(char, valid_chars)

    def test_filename_uniqueness(self):
        """Test that random_filename generates unique values."""
        filenames = [random_filename() for _ in range(100)]
        unique_filenames = set(filenames)
        
        # Most should be unique (allowing for extremely rare collisions)
        self.assertGreater(len(unique_filenames), 99)


class TestCreateRedirectHtml(unittest.TestCase):
    """Test suite for create_redirect_html function."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_creates_html_file(self):
        """Test that create_redirect_html creates an HTML file."""
        create_redirect_html(
            url="https://example.com/product",
            filename="test_file",
            title="Test Product",
            image_url="https://example.com/image.jpg",
            output_dir=self.test_dir
        )
        
        expected_file = os.path.join(self.test_dir, "test_file.html")
        self.assertTrue(os.path.exists(expected_file))

    def test_html_contains_redirect_url(self):
        """Test that generated HTML contains proper redirect URL."""
        test_url = "https://example.com/product?id=123"
        create_redirect_html(
            url=test_url,
            filename="test_redirect",
            title="Test",
            output_dir=self.test_dir
        )
        
        html_file = os.path.join(self.test_dir, "test_redirect.html")
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        self.assertIn(test_url, content)
        self.assertIn("window.location.replace", content)

    def test_html_contains_og_tags(self):
        """Test that generated HTML includes OGP meta tags."""
        title = "Product Title"
        create_redirect_html(
            url="https://example.com",
            filename="test_og",
            title=title,
            image_url="https://example.com/img.jpg",
            output_dir=self.test_dir
        )
        
        html_file = os.path.join(self.test_dir, "test_og.html")
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for OGP tags
        self.assertIn('og:title', content)
        self.assertIn('og:description', content)
        self.assertIn('og:image', content)
        self.assertIn('og:type', content)
        self.assertIn(title, content)

    def test_html_contains_twitter_tags(self):
        """Test that generated HTML includes Twitter card meta tags."""
        create_redirect_html(
            url="https://example.com",
            filename="test_twitter",
            title="Test Product",
            output_dir=self.test_dir
        )
        
        html_file = os.path.join(self.test_dir, "test_twitter.html")
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for Twitter tags
        self.assertIn('twitter:card', content)
        self.assertIn('twitter:title', content)
        self.assertIn('twitter:description', content)
        self.assertIn('twitter:image', content)

    def test_html_escapes_special_characters(self):
        """Test that special characters are properly escaped in HTML."""
        title_with_special = 'Product <script>alert("xss")</script>'
        create_redirect_html(
            url="https://example.com",
            filename="test_escape",
            title=title_with_special,
            output_dir=self.test_dir
        )
        
        html_file = os.path.join(self.test_dir, "test_escape.html")
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Should be escaped, not raw
        self.assertNotIn('<script>', content)
        self.assertIn('&lt;script&gt;', content)

    def test_html_has_valid_structure(self):
        """Test that generated HTML has valid basic structure."""
        create_redirect_html(
            url="https://example.com",
            filename="test_structure",
            output_dir=self.test_dir
        )
        
        html_file = os.path.join(self.test_dir, "test_structure.html")
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for required HTML elements
        self.assertIn('<!DOCTYPE html>', content)
        self.assertIn('<html', content)
        self.assertIn('<head>', content)
        self.assertIn('<meta charset', content)
        self.assertIn('</html>', content)


class TestGenerateShortUrl(unittest.TestCase):
    """Test suite for generate_short_url function."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    @patch('config_loader.load_secrets')
    def test_generates_short_url_with_correct_format(self, mock_load_secrets):
        """Test that generate_short_url returns properly formatted URL."""
        mock_load_secrets.return_value = {
            "base_url": "https://example.com/rktn"
        }
        
        short_url = generate_short_url(
            affiliate_url="https://rakuten.co.jp/item?id=123",
            product_name="Test Product",
            image_url="https://example.com/image.jpg",
            output_dir=self.test_dir
        )
        
        # Should start with base URL and end with .html
        self.assertTrue(short_url.startswith("https://example.com/rktn"))
        self.assertTrue(short_url.endswith(".html"))

    @patch('config_loader.load_secrets')
    def test_creates_redirect_html_file(self, mock_load_secrets):
        """Test that generate_short_url creates corresponding HTML file."""
        mock_load_secrets.return_value = {
            "base_url": "https://example.com/rktn"
        }
        
        short_url = generate_short_url(
            affiliate_url="https://rakuten.co.jp/item?id=456",
            product_name="Another Product",
            image_url="https://example.com/img2.jpg",
            output_dir=self.test_dir
        )
        
        # Extract filename from short URL
        filename = short_url.split("/")[-1]  # Gets "xxxxx.html"
        html_path = os.path.join(self.test_dir, filename)
        
        # File should exist
        self.assertTrue(os.path.exists(html_path))

    @patch('config_loader.load_secrets')
    def test_short_url_uniqueness(self, mock_load_secrets):
        """Test that each call generates a unique short URL."""
        mock_load_secrets.return_value = {
            "base_url": "https://example.com/rktn"
        }
        
        urls = [
            generate_short_url(
                affiliate_url=f"https://rakuten.co.jp/item?id={i}",
                product_name=f"Product {i}",
                image_url="https://example.com/image.jpg",
                output_dir=self.test_dir
            )
            for i in range(10)
        ]
        
        # All URLs should be unique
        unique_urls = set(urls)
        self.assertEqual(len(urls), len(unique_urls))

    @patch('config_loader.load_secrets')
    def test_product_name_in_html(self, mock_load_secrets):
        """Test that product name is included in the generated HTML."""
        mock_load_secrets.return_value = {
            "base_url": "https://example.com/rktn"
        }
        
        product_name = "Unique Test Product XYZ"
        short_url = generate_short_url(
            affiliate_url="https://rakuten.co.jp/item?id=789",
            product_name=product_name,
            image_url="https://example.com/image.jpg",
            output_dir=self.test_dir
        )
        
        # Extract filename and read HTML
        filename = short_url.split("/")[-1]
        html_path = os.path.join(self.test_dir, filename)
        
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Product name should be in the HTML (in OGP title)
        self.assertIn(product_name, content)


if __name__ == "__main__":
    unittest.main()
