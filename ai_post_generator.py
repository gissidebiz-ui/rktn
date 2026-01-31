import os
import csv
import random
import string
import subprocess
from google import genai

# ================================
# 1. Google AI API 設定
# ================================
client = genai.Client(api_key="AIzaSyAP81TrnMzM39gZsmdrDsy9EXzUTKZDSSA")

# ================================
# 2. 古いHTML削除（index.htmlだけ残す）
# ================================
def cleanup_html():
    for f in os.listdir("."):
        if f.endswith(".html") and f not in ["index.html"]:
            os.remove(f)

# ================================
# 3. ランダムファイル名生成
# ================================
def random_filename(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length)) + ".html"

# ================================
# 4. リダイレクトHTML生成
# ================================
def create_redirect_html(url, filename):
    html = f"""<!DOCTYPE html>
<html>
  <head>
    <meta http-equiv="refresh" content="0; URL={url}">
  </head>
  <body></body>
</html>
"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

# ================================
# 5. 短縮URL生成
# ================================
def generate_short_url(affiliate_url):
    filename = random_filename()
    create_redirect_html(affiliate_url, filename)
    return f"https://gissidebiz-ui.github.io/rakuten-shortener/{filename}"

# ================================
# 6. Google AI API で投稿文生成
# ================================
def generate_post_text(product_name, short_url):
    prompt = f"""
以下の情報から、X（旧Twitter）向けの投稿文を作成してください。

【商品名】
{product_name}

【短縮URL】
{short_url}

条件：
・140文字以内
・売れそうなキャッチコピー寄りの文体
・強すぎず自然なテンション
・絵文字は1〜2個だけ
・短縮URLは文末に置く
・宣伝臭くなりすぎない
・読みやすく、1ツイートで完結
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"[AI生成エラー] {product_name} → {short_url}"

# ================================
# 7. メイン処理
# ================================
def main():
    input_file = "input.csv"

    # 古いHTML削除
    cleanup_html()

    posts = []

    # CSV読み込み
    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            product_name = row[0]
            affiliate_url = row[1]

            # 短縮URL生成
            short_url = generate_short_url(affiliate_url)

            # AI投稿文生成
            post = generate_post_text(product_name, short_url)
            posts.append(post)

    # GitHubへ push（削除も含めて）
    subprocess.run(["git", "add", "-A"])
    subprocess.run(["git", "commit", "-m", "AI auto post update"])
    subprocess.run(["git", "push"])

    # 出力
    with open("posts.txt", "w", encoding="utf-8") as f:
        for p in posts:
            f.write(p + "\n\n")

    print("完了しました！ → posts.txt に投稿文を保存しました。")

if __name__ == "__main__":
    main()
