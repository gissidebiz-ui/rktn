import time
import random
from typing import Dict, List, Any
from di_container import get_container, DIContainer
from ai_helpers import generate_with_retry


class NormalPostGenerator:
    """Generator for normal X posts using dependency injection."""
    
    def __init__(self, container: DIContainer | None = None):
        """Initialize with optional DI container.
        
        Args:
            container: DI container instance (uses global if not provided)
        """
        self.container = container or get_container()
        self.config = self.container.get_generation_policy()
        self.accounts = self.container.get_accounts()
        self.themes = self.container.get_themes()
        self.client = self.container.get_ai_client()
    
    def generate_posts_for_theme(self, theme_key: str) -> List[str]:
        """Generate posts for a single theme.
        
        Args:
            theme_key: Theme name/key
            
        Returns:
            List of generated posts
        """
        prompt = self.themes[theme_key]
        posts = []
        
        posts_per_theme = self.config["normal_post_generation"]["posts_per_theme"]

        for i in range(posts_per_theme):
            print(f"生成中: {theme_key} → {i+1}/{posts_per_theme}")
            text = generate_with_retry(self.client, prompt, self.config["normal_post_generation"])
            text = text.replace("\n", "\\n")
            posts.append(text)

        # Retry failed posts
        def _is_failed(p: str | None) -> bool:
            if p is None:
                return True
            s = str(p).strip()
            return s == "" or s.startswith("[AIエラー]")

        failed_idxs = [i for i, p in enumerate(posts) if _is_failed(p)]
        if failed_idxs:
            retry_passes = self.config["normal_post_generation"]["retry_passes"]
            for rp in range(1, retry_passes + 1):
                print(f"[再試行パス {rp}/{retry_passes}] 空の生成結果を再実行します: {len(failed_idxs)} 件")
                for idx in failed_idxs[:]:
                    print(f"再試行: {theme_key} インデックス {idx+1}")
                    text = generate_with_retry(self.client, prompt, self.config["normal_post_generation"])
                    if text:
                        text = text.replace("\n", "\\n")
                    if not _is_failed(text):
                        posts[idx] = text
                        failed_idxs.remove(idx)
                if not failed_idxs:
                    break

        return posts

    def generate(self) -> None:
        """Generate posts for all accounts."""
        for account, data in self.accounts.items():
            theme_list = data.get("themes", [])

            print(f"\n=== {account} の通常ポスト生成開始 ===")

            # Select random themes
            selected_count = self.config["normal_post_generation"]["selected_themes_per_account"]
            selected_themes = random.sample(theme_list, min(selected_count, len(theme_list)))
            print(f"選択されたテーマ: {selected_themes}")

            all_posts = []

            for theme in selected_themes:
                posts = self.generate_posts_for_theme(theme)
                all_posts.extend(posts)

            output_path = f"../data/output/{account}_posts.txt"

            with open(output_path, "w", encoding="utf-8") as f:
                for p in all_posts:
                    f.write(p + "\n")

            print(f"{account} の通常ポスト {len(all_posts)}件を出力しました → {output_path}")

        print("\nすべてのアカウントの通常ポスト生成が完了しました！")


def main() -> None:
    """Main entry point."""
    generator = NormalPostGenerator()
    generator.generate()


if __name__ == "__main__":
    main()
