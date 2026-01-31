import os
import random
import string
import subprocess

def cleanup_all_html():
    for f in os.listdir("."):
        if f.endswith(".html") and f not in ["index.html"]:
            os.remove(f)

# ランダムなファイル名を生成
def generate_filename(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length)) + ".html"

# HTMLを生成
def generate_html(redirect_url):
    return f"""<!DOCTYPE html>
<html>
  <head>
    <meta http-equiv="refresh" content="0; URL={redirect_url}">
  </head>
  <body></body>
</html>
"""

# メイン処理
def create_short_url(affiliate_url):
    filename = generate_filename()
    filepath = os.path.join(".", filename)

    # HTMLを書き込み
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(generate_html(affiliate_url))

    # Git コマンド実行（削除も含めて add）
    subprocess.run(["git", "add", "-A"])
    subprocess.run(["git", "commit", "-m", "Cleanup old files and add new ones"])
    subprocess.run(["git", "push"])

    # 完成した短縮URL
    short_url = f"https://gissidebiz-ui.github.io/rakuten-shortener/{filename}"
    return short_url

# 実行例
if __name__ == "__main__":
    cleanup_all_html()
    url = input("楽天アフィリエイトURLを入力してください：")
    print("短縮URLを生成中…")
    result = create_short_url(url)
    print("短縮URL：", result)
