"""
Remove leading \\n from merged output files - only at line start
Dynamically fetches account names from config_loader
"""
import os
import re
import sys
sys.path.insert(0, os.path.dirname(__file__))
from config_loader import load_accounts

output_dir = r"../data/output"

# 設定からアカウント名を動的に取得
accounts = load_accounts()
if isinstance(accounts, dict):
    account_names = list(accounts.keys())
else:
    # リスト形式の場合（name キーを持つ）
    account_names = [acc.get("name") if isinstance(acc, dict) else acc for acc in accounts]

# アカウント名からマージファイル名を生成
files = [f"{name}_merged.txt" for name in account_names]

print(f"処理対象アカウント: {', '.join(account_names)}")
print(f"処理対象ファイル: {files}\n")

processed_count = 0
for filename in files:
    filepath = os.path.join(output_dir, filename)
    
    # ファイルが存在しない場合はスキップ
    if not os.path.exists(filepath):
        print(f"⊘ {filename}: ファイルが存在しません（スキップ）")
        continue
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # 各行の先頭の \\n のみ削除
        new_lines = []
        removed_count = 0
        for line in lines:
            # 先頭の \\n を削除
            if line.startswith("\\n"):
                new_line = line[2:]  # \\n は2文字なので [2:] で削除
                new_lines.append(new_line)
                removed_count += 1
            else:
                new_lines.append(line)
        
        # ファイルに上書き
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        
        print(f"✓ {filename}: 先頭の\\n を {removed_count} 行削除しました")
        processed_count += 1
    except Exception as e:
        print(f"✗ {filename}: エラーが発生しました - {e}")

print(f"\n完了：{processed_count}/{len(files)} ファイルを処理しました")
