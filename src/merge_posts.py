import os
from typing import List, Dict, Any
from di_container import get_container, DIContainer


class PostMerger:
    """依存性の注入 (DI) を利用して、生成されたポストファイルをマージするクラス。"""
    
    def __init__(self, container: DIContainer | None = None):
        """初期化。DI コンテナをオプションで指定可能です。
        
        Args:
            container: DI コンテナインスタンス（指定がない場合はグローバルなコンテナを使用）
        """
        self.container = container or get_container()
        self.accounts = self.container.get_accounts()
    
    @staticmethod
    def merge_alternate(lines1: List[str], lines2: List[str]) -> List[str]:
        """2 つのポストリストを交互にマージします。
        
        Args:
            lines1: リスト1（例: アフィリエイトポスト）
            lines2: リスト2（例: 通常ポスト）
            
        Returns:
            交互に入れ替えられたマージ後のリスト
        """
        max_len = max(len(lines1), len(lines2))
        merged = []

        for i in range(max_len):
            if i < len(lines1):
                merged.append(lines1[i].rstrip("\n"))
            if i < len(lines2):
                merged.append(lines2[i].rstrip("\n"))

        return merged

    def merge(self) -> None:
        """全アカウントのアフィリエイトポストと通常ポストをマージし、中間ファイルを削除します。"""
        base_path = "../data/output"

        if not os.path.exists(base_path):
            print(f"[ERROR] 出力フォルダが見つかりません: {base_path}")
            return

        for account in self.accounts.keys():
            aff_file = os.path.join(base_path, f"{account}_affiliate_posts.txt")
            post_file = os.path.join(base_path, f"{account}_posts.txt")

            # 片方のファイルが欠けている場合はスキップ
            if not os.path.exists(aff_file) or not os.path.exists(post_file):
                print(f"[SKIP] {account}: 必要なファイルが揃っていないためマージをスキップします")
                continue

            print(f"[MERGE] {account} のポストをマージしています...")

            # Windows 等での文字化けを防ぐため、UTF-8-SIG (BOM付き) で読み込みます。
            with open(aff_file, "r", encoding="utf-8-sig") as f1:
                lines1 = f1.readlines()

            with open(post_file, "r", encoding="utf-8-sig") as f2:
                lines2 = f2.readlines()

            # 交互マージの実行
            merged = self.merge_alternate(lines1, lines2)

            output_file = os.path.join(base_path, f"{account}_merged.txt")

            # 最終的なマージ後ファイルを書き出し
            with open(output_file, "w", encoding="utf-8") as out:
                out.write("\n".join(merged))

            # 中間ファイルを削除してストレージをクリーンに保つ
            os.remove(aff_file)
            os.remove(post_file)

            print(f"[DONE] {account}: merged.txt を作成し、中間ファイルを削除しました")


def main() -> None:
    """メインエントリポイント。"""
    merger = PostMerger()
    merger.merge()


if __name__ == "__main__":
    main()
