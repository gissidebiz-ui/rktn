import subprocess

def run_script(script_name):
    print(f"\n=== {script_name} を実行中… ===")
    result = subprocess.run(["python", script_name])
    if result.returncode != 0:
        print(f"エラー: {script_name} の実行に失敗しました")
        exit(1)

def main():
    print("★ 自動処理開始 ★")

    # 1. input.csv を自動生成
    run_script("make_input_csv.py")

    # 2. AI投稿文生成（短縮URL＋140文字投稿文）
    run_script("ai_post_generator.py")

    print("\n★ 全処理が完了しました！ ★")
    print("Twittbot に貼るだけの投稿文が posts.txt に出力されています。")

if __name__ == "__main__":
    main()
