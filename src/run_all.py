import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import time
import subprocess
import yaml  # type: ignore
from datetime import datetime, timedelta
from merge_posts import PostMerger
from di_container import get_container

# ================================
# 日別ログファイルのパス生成
# ================================
def get_log_path():
    today = datetime.now().strftime("%Y-%m-%d")
    return f"../logs/log_{today}.txt"

# ================================
# ログ書き込み関数（ターミナル + ファイル）
# ================================
def log(message):
    os.makedirs("../logs", exist_ok=True)

    log_path = get_log_path()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

    print(message)

# ================================
# 古いログ（30日以上前）を削除
# ================================
def cleanup_old_logs():
    log_dir = "../logs"
    if not os.path.exists(log_dir):
        return

    threshold = datetime.now() - timedelta(days=30)

    for filename in os.listdir(log_dir):
        if filename.startswith("log_") and filename.endswith(".txt"):
            date_str = filename.replace("log_", "").replace(".txt", "")
            try:
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < threshold:
                    os.remove(os.path.join(log_dir, filename))
                    print(f"古いログを削除しました: {filename}")
            except ValueError:
                continue

# ================================
# secrets.yaml チェック
# ================================
def check_secrets():
    secrets_path = "../config/secrets.yaml"
    if not os.path.exists(secrets_path):
        log("⚠ エラー: secrets.yaml が見つかりません。処理を停止します。")
        log("テンプレート生成スクリプトを実行してください: python secrets_template_generator.py")
        exit(1)

# ================================
# accounts.yaml 読み込み
# ================================
def load_accounts():
    accounts_path = "../config/accounts.yaml"
    if not os.path.exists(accounts_path):
        log("⚠ エラー: accounts.yaml が見つかりません。処理を停止します。")
        exit(1)

    with open(accounts_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return list(data.keys())  # アカウント名だけ返す

# ================================
# スクリプト実行
# ================================
def run_script(script_name):
    log(f"=== {script_name} を実行開始 ===")
    result = subprocess.run(["python", script_name])
    if result.returncode != 0:
        log(f"エラー: {script_name} の実行に失敗しました")
        exit(1)
    log(f"=== {script_name} を正常終了 ===")

# ================================
# メイン処理
# ================================
def main():
    cleanup_old_logs()
    log("★ 自動処理開始 ★")

    start_time = time.time()

    check_secrets()

    # 前回のメトリクスログをクリア（今回実行分のみ集計するため）
    try:
        os.makedirs("../logs", exist_ok=True)
        metrics_path = os.path.join("..", "logs", "ai_metrics.jsonl")
        if os.path.exists(metrics_path):
            os.remove(metrics_path)
    except Exception:
        pass

    # 投稿生成スクリプト
    run_script("make_input_csv.py")
    run_script("normal_post_generator.py")
    run_script("affiliate_post_generator.py")

    # 投稿文マージ処理（DIコンテナ使用）
    merger = PostMerger()
    merger.merge()
    log("投稿文のマージ処理が完了しました。")

    # AI メトリクス集計
    try:
        metrics_path = os.path.join("..", "logs", "ai_metrics.jsonl")
        if os.path.exists(metrics_path):
            import json
            counts = {}
            attempts_list = []
            with open(metrics_path, "r", encoding="utf-8") as mf:
                for line in mf:
                    try:
                        obj = json.loads(line)
                        ev = obj.get("event")
                        counts[ev] = counts.get(ev, 0) + 1
                        info = obj.get("info") or {}
                        if ev == "ai_success":
                            attempts_list.append(info.get("attempts", 1))
                    except Exception:
                        continue

            log("--- AI 呼び出しサマリ ---")
            log(f"AI リクエスト合計イベント数: {sum(counts.values())}")
            log(f"成功 (ai_success): {counts.get('ai_success', 0)}")
            log(f"リクエスト開始 (ai_request_start): {counts.get('ai_request_start', 0)}")
            log(f"エラー (ai_error): {counts.get('ai_error', 0)}")
            log(f"レート制限検出 (ai_rate_limit): {counts.get('ai_rate_limit', 0)}")
            log(f"最終失敗 (ai_final_failure): {counts.get('ai_final_failure', 0)}")
            if attempts_list:
                avg_attempts = sum(attempts_list) / len(attempts_list)
                log(f"平均成功までの試行回数: {avg_attempts:.2f}")
            log("--- AI 呼び出しサマリ 終了 ---")
        else:
            log("AI メトリクスファイルが見つかりませんでした（ai_metrics.jsonl）。")
    except Exception as e:
        log(f"AI メトリクス集計でエラー: {e}")

    end_time = time.time()
    elapsed = end_time - start_time

    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    log(f"★ 全処理が完了しました（総実行時間: {minutes}分 {seconds}秒） ★")
    log("Twittbot に貼るだけの投稿文が data/output に出力されています。")

    print("\n★ 全処理が完了しました！ ★")
    print(f"総実行時間: {minutes}分 {seconds}秒")
    print("Twittbot に貼るだけの投稿文が data/output に出力されています。")

if __name__ == "__main__":
    main()
