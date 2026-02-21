import os
from typing import List, Dict, Any
from di_container import get_container, DIContainer


class PostMerger:
    """Post file merger using dependency injection."""
    
    def __init__(self, container: DIContainer | None = None):
        """Initialize with optional DI container.
        
        Args:
            container: DI container instance (uses global if not provided)
        """
        self.container = container or get_container()
        self.accounts = self.container.get_accounts()
    
    @staticmethod
    def merge_alternate(lines1: List[str], lines2: List[str]) -> List[str]:
        """Merge two lists of lines alternately.
        
        Args:
            lines1: First list of lines
            lines2: Second list of lines
            
        Returns:
            Merged list of lines
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
        """Merge affiliate and normal posts for all accounts."""
        base_path = "../data/output"

        if not os.path.exists(base_path):
            print(f"[ERROR] 出力フォルダが見つかりません: {base_path}")
            return

        for account in self.accounts.keys():
            aff_file = os.path.join(base_path, f"{account}_affiliate_posts.txt")
            post_file = os.path.join(base_path, f"{account}_posts.txt")

            if not os.path.exists(aff_file) or not os.path.exists(post_file):
                print(f"[SKIP] {account}: 必要なファイルがありません")
                continue

            print(f"[MERGE] {account} を処理中...")

            # UTF-8-SIG で読み込む（ここが重要）
            with open(aff_file, "r", encoding="utf-8-sig") as f1:
                lines1 = f1.readlines()

            with open(post_file, "r", encoding="utf-8-sig") as f2:
                lines2 = f2.readlines()

            merged = self.merge_alternate(lines1, lines2)

            # Cleanup literal \\n strings which sometimes appear in AI output
            cleaned_merged = []
            for line in merged:
                # Remove leading \\n (2 characters)
                if line.startswith("\\n"):
                    line = line[2:]
                # Remove any other literal \\n sequences
                line = line.replace("\\n", "")
                cleaned_merged.append(line)

            output_file = os.path.join(base_path, f"{account}_merged.txt")

            # 出力は通常の UTF-8 でOK
            with open(output_file, "w", encoding="utf-8") as out:
                out.write("\n".join(cleaned_merged))

            os.remove(aff_file)
            os.remove(post_file)

            print(f"[DONE] {account}: merged.txt 作成 (クリーンアップ済) & 元ファイル削除完了")


def main() -> None:
    """Main entry point."""
    merger = PostMerger()
    merger.merge()


if __name__ == "__main__":
    main()
