"""
AI 支援モジュール。
AI クライアントの生成と、再試行ロジックを含むコンテンツ生成を担当します。
"""
from google import genai
import threading
import time
from typing import Dict, Any
import retry_helper


# === 15 RPM 制限回避用（Gemini無料枠対策） ===
_api_lock = threading.Lock()
_last_api_call_time = 0.0
API_CALL_INTERVAL_SECONDS = 4.1

def _enforce_rate_limit():
    """グローバルロックを用いて、API呼び出し間の最低インターバルを保証する"""
    global _last_api_call_time
    with _api_lock:
        now = time.time()
        elapsed = now - _last_api_call_time
        if elapsed < API_CALL_INTERVAL_SECONDS:
            time.sleep(API_CALL_INTERVAL_SECONDS - elapsed)
        _last_api_call_time = time.time()


def create_ai_client(api_key: str) -> genai.Client:
    """Google 外部 AI (Gemini) クライアントを作成して返します。
    
    Args:
        api_key: 認証用の Google API キー
        
    Returns:
        genai.Client: 設定済みの AI クライアントインスタンス
    """
    return genai.Client(api_key=api_key)


def generate_with_retry(client: genai.Client, prompt: str, config: Dict[str, Any]) -> str:
    """
    指数バックオフとジッター再試行ロジックを用いて、AI からコンテンツを生成します。
    
    Args:
        client: Google 外部 AI クライアント
        prompt: 生成用のプロンプトテキスト
        config: generation_policy.yaml から読み込まれた再試行設定を含む辞書
                期待されるキー: max_retries, model_name, retry_base_backoff 等
    
    Returns:
        生成されたテキスト。すべての再試行が失敗した場合は空文字列を返します。
    """
    max_retries = config.get("max_retries", 8)
    
    for attempt in range(1, max_retries + 1):
        try:
            # リクエスト開始をログに記録
            try:
                retry_helper.metrics_log("ai_request_start", {"attempt": attempt})
            except Exception:
                pass
            
            # APIの呼び出し間隔を厳密に管理 (429エラー防止)
            _enforce_rate_limit()

            # AI への生成リクエスト実行
            model_name = config.get("model_name", "gemini-2.0-flash")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )

            # 正常な応答の処理
            if hasattr(response, "text") and response.text:
                try:
                    retry_helper.metrics_log("ai_success", {"attempts": attempt})
                except Exception:
                    pass
                return response.text.strip()
            else:
                # text 属性がない場合のフォールバック（候補から直接取得）
                try:
                    retry_helper.metrics_log("ai_success", {"attempts": attempt})
                except Exception:
                    pass
                return response.candidates[0].content.parts[0].text.strip()

        except Exception as e:
            # エラー情報の取得とログ記録
            err_text = str(e)
            
            try:
                retry_helper.metrics_log("ai_error", {"attempt": attempt, "error": err_text})
            except Exception:
                pass

            # 最大リトライ回数に達したか確認
            if attempt == max_retries:
                print("[!] 最大リトライ到達。空の結果を返します。")
                try:
                    retry_helper.metrics_log("ai_final_failure", {"attempts": attempt, "error": err_text})
                except Exception:
                    pass
                return ""

            # レート制限 (429等) によるエラーかどうかを判定
            is_rate_limit = retry_helper.should_retry_on_error(err_text)
            
            if is_rate_limit:
                try:
                    retry_helper.metrics_log("ai_rate_limit", {"attempt": attempt})
                except Exception:
                    pass

            # 待機時間を計算し、スリープを実行
            backoff_result = retry_helper.calculate_backoff(attempt, is_rate_limit, config)
            
            # calculate_backoff がタプル (backoff, jitter, sleep_time) か単一の数値を返すかに対応
            if isinstance(backoff_result, tuple):
                backoff, jitter, sleep_time = backoff_result
            else:
                sleep_time = backoff_result
                backoff = None
            
            retry_helper.log_retry_attempt(attempt, max_retries, err_text, sleep_time, backoff)
            time.sleep(sleep_time)

    return ""
