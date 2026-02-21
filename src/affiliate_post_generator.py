import os
import csv
import glob
import time
import subprocess
import re
from typing import Dict, List, Any
from di_container import get_container, DIContainer
from ai_helpers import generate_with_retry
from html_generator import generate_short_url


class AffiliatePostGenerator:
    """Generator for affiliate X posts using dependency injection."""
    
    def __init__(self, container: DIContainer | None = None):
        """Initialize with optional DI container.
        
        Args:
            container: DI container instance (uses global if not provided)
        """
        self.container = container or get_container()
        self.config = self.container.get_generation_policy()
        self.accounts = self.container.get_accounts()
        self.client = self.container.get_ai_client()
    
    def cleanup_html(self) -> None:
        """Remove old HTML files based on retention policy."""
        html_dir = "../html"
        now = time.time()
        
        # Get retention settings from config
        html_config = self.config.get("html_cleanup", {})
        retention_days = self.config.get("affiliate_post_generation", {}).get("html_retention_days", 5)
        seconds_in_retention = retention_days * 24 * 60 * 60
        
        excluded_files = html_config.get("excluded_files", ["index.html"])
        extensions = html_config.get("default_extensions", [".html"])

        for f in os.listdir(html_dir):
            # Skip excluded files and non-matching extensions
            if f in excluded_files or not any(f.endswith(ext) for ext in extensions):
                continue
                
            file_path = os.path.join(html_dir, f)
            file_mtime = os.path.getmtime(file_path)
            
            # Delete files older than retention period
            if now - file_mtime > seconds_in_retention:
                try:
                    os.remove(file_path)
                    print(f"削除しました: {f} ({retention_days}日以上経過)")
                except Exception as e:
                    print(f"削除失敗: {f} - {e}")

    def generate_post_text(self, product_name: str, short_url: str) -> str:
        """Generate affiliate post text.
        
        Args:
            product_name: Product name
            short_url: Shortened URL
            
        Returns:
            Generated post text
        """
        max_name_len = self.config["affiliate_post_generation"].get("max_product_name_length", 80)
        safe_name = product_name[:max_name_len]

        prompt = f"""
以下の情報から、X（旧Twitter）向けの投稿文を作成してください。
※文章の中にURLは絶対に含めないでください。

【商品名】
{safe_name}

条件：
・本文は50文字以内
・売れそうなキャッチコピー寄り
・強すぎず自然なテンション
・絵文字は1つだけ
・短縮URLは文末に置く
・宣伝臭くしない
・1行で完結（改行しない）
"""
        text = generate_with_retry(self.client, prompt, self.config["affiliate_post_generation"])
        
        # Remove unwanted URLs
        text = re.sub(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+', '', text).strip()
        
        # Handle hashtags
        if "#" in text:
            text = text.replace(" #", "\\n#").replace("　#", "\\n#")
            text = re.sub(r'([^\\n])#', r'\1\\n#', text)

        # Final assembly
        return f"{text}\\n\\n{short_url}"

    def generate(self) -> None:
        """Generate affiliate posts for all accounts."""
        self.cleanup_html()

        input_files = glob.glob("../data/input/*_input.csv")

        for input_path in input_files:
            filename = os.path.basename(input_path)
            account = filename.replace("_input.csv", "")

            output_path = f"../data/output/{account}_affiliate_posts.txt"
            posts = []

            # Read input CSV and generate short URLs
            entries = []
            with open(input_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    try:
                        if len(row) < 3:
                            continue
                        product_name = row[0]
                        affiliate_url = row[1]
                        image_url = row[2]

                        short_url = generate_short_url(affiliate_url, product_name, image_url)
                        entries.append({
                            "product_name": product_name,
                            "short_url": short_url,
                            "post": None
                        })
                    except Exception as e:
                        print(f"[ERROR] 行処理失敗: {row}")
                        import traceback
                        traceback.print_exc()
                        continue

            # Generate initial posts
            for e in entries:
                e["post"] = self.generate_post_text(e["product_name"], e["short_url"])

            # Retry failed posts
            def _is_failed(p: str | None) -> bool:
                if p is None:
                    return True
                s = str(p).strip()
                return s == "" or s.startswith("[AIエラー]")

            failed_idxs = [i for i, e in enumerate(entries) if _is_failed(e.get("post"))]
            if failed_idxs:
                retry_passes = self.config["affiliate_post_generation"].get("retry_passes", 3)
                for rp in range(1, retry_passes + 1):
                    print(f"[再試行パス {rp}/{retry_passes}] アフィリエイト投稿の空結果を再実行します: {len(failed_idxs)} 件")
                    for idx in failed_idxs[:]:
                        e = entries[idx]
                        try:
                            new_post = self.generate_post_text(e["product_name"], e["short_url"])
                            if not _is_failed(new_post):
                                entries[idx]["post"] = new_post
                                failed_idxs.remove(idx)
                        except Exception as ex:
                            print(f"[ERROR] 再試行で失敗: {e['product_name']}")

            # Write output
            for e in entries:
                posts.append(e.get("post") or "")

            with open(output_path, "w", encoding="utf-8") as f:
                for p in posts:
                    safe_post = p.replace("\\\\n", "\\n")
                    f.write(safe_post + "\n")

            print(f"{output_path} を生成しました！")

        try:
            subprocess.run(["git", "add", "-A"], check=True)
            subprocess.run(["git", "commit", "-m", "AI auto post update"], check=True)
            subprocess.run(["git", "push"], check=True)
        except Exception as e:
            print(f"GitHub push エラー: {e}")

        print("全アカウントのアフィリエイト投稿文生成が完了しました！")


def main() -> None:
    """Main entry point."""
    generator = AffiliatePostGenerator()
    generator.generate()


if __name__ == "__main__":
    main()
