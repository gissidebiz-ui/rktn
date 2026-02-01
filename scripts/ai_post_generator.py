import os
import csv
import glob
import random
import string
import time
import subprocess
from google import genai

# ================================
# 1. Google AI API 設定
# ================================
client = genai.Client(api_key="AIzaSyAP81TrnMzM39gZsmdrDsy9EXzUTKZDSSA")  # ← あなたのキーを入れる

# ================================
# 2. 古いHTML削除（index.htmlだけ残す）
# ================================
def cleanup_html():
    html_dir = "../html"
    for f in os.listdir(html_dir):
        if f.endswith(".html") and f not in ["index.html"]:
            os.remove(os.path.join(html_dir, f))

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
    with open(f"../html/{filename}", "w", encoding="utf-8") as f:
        f.write(html)

# ================================
# 5. 短縮URL生成
# ================================
def generate_short_url(affiliate_url):
    filename = random_filename()
    create_redirect_html(affiliate_url, filename)
    return f"https://gissidebiz-ui.github.io/rakuten-shortener/{filename}"

# ================================
# 6. AI呼び出し（リトライ付き）
# ================================
def generate_with_retry(prompt, max_retries=5):
    for i in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )

            # 新SDKのレスポンス形式に対応
            if hasattr(response, "text") and response.text:
                return response.text.strip()
            else:
                return response.candidates[0].content.parts[0].text.strip()

        except Exception as e:
            # wait = 1 + i
            wait = 1 
            print(f"AI呼び出し失敗: {e} → {wait}秒待機して再試行")
            time.sleep(wait)

    return "[AIエラー] 最大リトライ回数を超えました"

# ================================
# 7. 投稿文生成
# ================================
def generate_post_text(product_name, short_url):
    safe_name = product_name[:80]

    prompt = f"""
以下の情報から、X（旧Twitter）向けの投稿文を作成してください。

【商品名】
{safe_name}

【短縮URL】
{short_url}

条件：
・本文は50文字以内
・売れそうなキャッチコピー寄り
・強すぎず自然なテンション
・絵文字は1つだけ
・短縮URLは文末に置く
・宣伝臭くしない
・1行で完結（改行しない）
"""

    text = generate_with_retry(prompt)

    # 改行を \n に変換して1行にする
    text = text.replace("\n", "\\n")

    # 50文字以内に強制トリム
    if len(text) > 50:
        text = text[:50]

    return f"{text} {short_url}"

# ================================
# 8. メイン処理
# ================================


def main():

    # 古いHTML削除
    cleanup_html()

    # ../data/input/ 内の *_input.csv を全部取得
    input_files = glob.glob("../data/input/*_input.csv")

    for input_path in input_files:
        filename = os.path.basename(input_path)

        # アカウント名を抽出（例：puu_input.csv → puu）
        account = filename.replace("_input.csv", "")

        output_path = f"../data/output/{account}_posts.txt"
        posts = []

        # CSV読み込み
        with open(input_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                product_name = row[0]
                affiliate_url = row[1]

                short_url = generate_short_url(affiliate_url)
                post = generate_post_text(product_name, short_url)
                posts.append(post)

        # 出力
        with open(output_path, "w", encoding="utf-8") as f:
            for p in posts:
                f.write(p + "\n")

        print(f"{output_path} を生成しました！")

    # GitHub push（任意）
    try:
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "commit", "-m", "AI auto post update"], check=True)
        subprocess.run(["git", "push"], check=True)
    except Exception as e:
        print(f"GitHub push エラー: {e}")

    print("全アカウントの投稿文生成が完了しました！")

if __name__ == "__main__":
    main()
