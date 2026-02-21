import time
import random
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any
from di_container import get_container, DIContainer
from ai_helpers import generate_with_retry


class NormalPostGenerator:
    """依存性の注入 (DI) を利用して X (旧 Twitter) の通常ポストを生成するクラス。"""
    
    def __init__(self, container: DIContainer | None = None):
        """初期化。DI コンテナをオプションで指定可能です。
        
        Args:
            container: DI コンテナインスタンス（指定がない場合はグローバルなコンテナを使用）
        """
        self.container = container or get_container()
        self.config = self.container.get_generation_policy()
        self.accounts = self.container.get_accounts()
        self.themes = self.container.get_themes()
        self.client = self.container.get_ai_client()
        self.logger: logging.Logger = self.container.get_logger(__name__)
    
    def generate_posts_for_theme(self, theme_key: str) -> List[str]:
        """特定のテーマに基づいて複数のポスト文案を生成します。
        
        Args:
            theme_key: テーマの名称またはキー
            
        Returns:
            生成されたポスト文案（改行を \\n に変換済み）のリスト
        """
        prompt = self.themes[theme_key]
        posts = []
        
        def generate_single_post(index):
            print(f"生成中: {theme_key} → {index+1}/{posts_per_theme}")
            self.logger.debug(f"テーマ '{theme_key}' のポスト生成中 ({index+1}/{posts_per_theme})")
            text = generate_with_retry(self.client, prompt, self.config["normal_post_generation"])
            # CSV 保存時に 1 行に収めるため、改行をリテラル表現に変換
            text = text.replace("\n", "\\n")
            
            # --- 不要な文字列（ノイズ）の除去 ---
            import re
            # 1. 見出し（【...】）や「例：」などを削除
            text = re.sub(r'^【.*?】', '', text)
            text = re.sub(r'^例[1-9]：', '', text)
            text = re.sub(r'^例：', '', text)
            # 2. AIのメタ的な発言（〜パターン等）を削除
            text = re.sub(r'上記例を参考にして.*', '', text)
            text = re.sub(r'他に\d+パターン.*', '', text)
            
            return text.strip()

        # 設定ファイルからテーマあたりの生成件数を取得
        posts_per_theme = self.config["normal_post_generation"]["posts_per_theme"]

        # AIのレート制限を考慮し、並列数を制限（例：最大5並列）
        with ThreadPoolExecutor(max_workers=5) as executor:
            posts = list(executor.map(generate_single_post, range(posts_per_theme)))

        # 生成に失敗（空文字やエラーメッセージ）したポストの再試行処理
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
                self.logger.info(f"再試行パス {rp}/{retry_passes}: 失敗したポスト {len(failed_idxs)} 件")
                for idx in failed_idxs[:]:
                    print(f"再試行: {theme_key} インデックス {idx+1}")
                    text = generate_with_retry(self.client, prompt, self.config["normal_post_generation"])
                    if text:
                        text = text.replace("\n", "\\n")
                    if not _is_failed(text):
                        posts[idx] = text
                        failed_idxs.remove(idx)
                if not failed_idxs: # 全て成功したらループを抜ける
                    break

        return posts

    def generate(self) -> None:
        """全アカウントに対してポスト生成処理を実行します。"""
        for account, data in self.accounts.items():
            theme_list = data.get("themes", [])

            print(f"\n=== {account} の通常ポスト生成開始 ===")
            self.logger.info(f"アカウント '{account}' の通常ポスト生成を開始します")

            # アカウントごとに指定された件数のテーマをランダムに選択
            selected_count = self.config["normal_post_generation"]["selected_themes_per_account"]
            selected_themes = random.sample(theme_list, min(selected_count, len(theme_list)))
            print(f"選択されたテーマ: {selected_themes}")
            self.logger.debug(f"選択済みテーマ: {selected_themes}")
            all_posts = []
            for theme in selected_themes:
                posts = self.generate_posts_for_theme(theme)
                all_posts.extend(posts)

            # 順序をランダムに入れ替え
            random.shuffle(all_posts)
            output_path = f"../data/output/{account}_posts.txt"

            # 結果をテキストファイルに出力
            with open(output_path, "w", encoding="utf-8") as f:
                for p in all_posts:
                    f.write(p + "\n")

            print(f"{account} の通常ポスト {len(all_posts)}件を出力しました → {output_path}")

        print("\nすべてのアカウントの通常ポスト生成が完了しました！")


def main() -> None:
    """メインエントリポイント。"""
    generator = NormalPostGenerator()
    generator.generate()


if __name__ == "__main__":
    main()
