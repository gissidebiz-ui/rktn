"""
HTML generator module.
Handles creation of redirect HTML pages with OGP tags.
"""
import os
import string
import random
import html as html_module
from typing import Optional
import config_loader
# Provide a module-level alias for tests that patch html_generator.load_secrets
load_secrets = config_loader.load_secrets


def random_filename(length: int = 6) -> str:
    """Generate a random filename without .html extension.
    
    Args:
        length: Length of generated filename (default: 6)
        
    Returns:
        Random filename string with lowercase letters and digits
    """
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def create_redirect_html(
    url: str,
    filename: str,
    title: str = "商品詳細はこちら",
    image_url: str = "",
    output_dir: str = "../html"
) -> None:
    """
    Create redirect HTML page with OGP tags for social media previews.
    
    Args:
        url: Target redirect URL
        filename: Filename (without .html extension)
        title: Page title for OGP
        image_url: Image URL for OGP og:image
        output_dir: Output directory for HTML files
    """
    # Escape attribute values for safety
    safe_title = html_module.escape(title)
    safe_image_url = html_module.escape(image_url) if image_url else ""
    
    og_description = f"楽天 - {safe_title}"
    
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{safe_title}</title>
    <meta property="og:title" content="{safe_title}">
    <meta property="og:description" content="{og_description}">
    <meta property="og:image" content="{safe_image_url}">
    <meta property="og:type" content="product">
    <meta property="og:url" content="{url}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{safe_title}">
    <meta name="twitter:description" content="{og_description}">
    <meta name="twitter:image" content="{safe_image_url}">
    <script>
      window.location.replace("{url}");
    </script>
  </head>
  <body></body>
</html>
"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(f"{output_dir}/{filename}.html", "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        print(f"[ERROR] ファイル保存失敗: {e}")


def generate_short_url(
    affiliate_url: str,
    product_name: str,
    image_url: str,
    output_dir: str = "../html"
) -> str:
    """
    Generate a short URL by creating redirect HTML and returning shortened URL.
    
    Args:
        affiliate_url: Target affiliate URL
        product_name: Product name for OGP title
        image_url: Product image URL
        output_dir: Directory for HTML file
    
    Returns:
        str: Short URL in format {BASE_URL}/{filename}.html
    """
    secrets = config_loader.load_secrets()
    BASE_URL = secrets.get("base_url", "")

    filename = random_filename()
    create_redirect_html(affiliate_url, filename, product_name, image_url, output_dir)
    
    return f"{BASE_URL}/{filename}.html"
