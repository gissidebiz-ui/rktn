/**
 * ============================================================
 * Config.gs — 設定管理モジュール
 * ============================================================
 * スクリプトプロパティから API キーを安全に取得し、
 * 各アカウントの属性（ペルソナ）やスケジュールを一元管理します。
 *
 * 【シートコピー後のセットアップ】
 * 1. GAS エディタ → プロジェクトの設定 → スクリプトプロパティ
 * 2. 以下のキーを登録（アカウントごとに固有値を設定）:
 *    - GEMINI_API_KEY, THREADS_ACCESS_TOKEN, THREADS_USER_ID, RAKUTEN_APP_ID
 * ============================================================
 */

// ================================
// APIキー/ID取得（スクリプトプロパティ）
// ================================
const CONFIG = {
  get GEMINI_API_KEY() {
    return (
      PropertiesService.getScriptProperties().getProperty("GEMINI_API_KEY") ||
      ""
    );
  },
  get THREADS_ACCESS_TOKEN() {
    return (
      PropertiesService.getScriptProperties().getProperty(
        "THREADS_ACCESS_TOKEN",
      ) || ""
    );
  },
  get THREADS_USER_ID() {
    return (
      PropertiesService.getScriptProperties().getProperty("THREADS_USER_ID") ||
      ""
    );
  },
  get RAKUTEN_APP_ID() {
    return (
      PropertiesService.getScriptProperties().getProperty("RAKUTEN_APP_ID") ||
      ""
    );
  },
  get RAKUTEN_AFFILIATE_ID() {
    return (
      PropertiesService.getScriptProperties().getProperty(
        "RAKUTEN_AFFILIATE_ID",
      ) || ""
    );
  },
};

// ================================
// トレンド解析・ペルソナ設定
// ================================
const TREND_CONFIG = {
  // 【最重要】アカウントのペルソナ。ここを書き換えるだけで投稿内容が激変します
  TARGET_DEMO:
    "30代男性、ビジネスマン、効率化・最新ガジェット愛好家。等身大で有益な情報を発信するスタイル。",

  CACHE_KEY: "TREND_CACHE",
  CACHE_TIMESTAMP_KEY: "TREND_CACHE_TS",
  CACHE_DURATION_HOURS: 6,
};

// ================================
// スケジューリング設定
// ================================
const SCHEDULE_CONFIG = {
  QUIET_HOURS_START: 0,
  QUIET_HOURS_END: 7,

  // 全時間帯 60分固定
  NORMAL_INTERVAL_MIN: 60,
  NORMAL_INTERVAL_MAX: 60,

  // 自然な投稿時間の揺らぎ（0〜5分）
  JITTER_MAX_MIN: 5,
};

// ================================
// 投稿生成設定
// ================================
const POST_CONFIG = {
  NORMAL_POST_MAX_CHARS: 500,
  AFFILIATE_POST_MIN_CHARS: 200,
  AFFILIATE_POST_MAX_CHARS: 500,

  // 黄金比（通常 3 : アフィリエイト 1）
  NORMAL_POSTS_PER_SET: 3,
  AFFILIATE_POSTS_PER_SET: 1,
  TOTAL_POSTS_PER_SET: 4,
};

// ================================
// 各種 API 内部設定
// ================================
const GEMINI_CONFIG = {
  MODEL: "gemini-2.0-flash",
  BASE_URL: "https://generativelanguage.googleapis.com/v1beta/models/",
  MAX_RETRIES: 2, // タイムアウト防止のため制限
  RETRY_DELAY_MS: 1000,
};

const THREADS_API_CONFIG = {
  BASE_URL: "https://graph.threads.net/v1.0",
  PUBLISH_WAIT_MS: 5000,
  REPLY_DELAY_MS: 3000,
};

const SHEET_COLUMNS = {
  SCHEDULED_TIME: 1,
  POST_TYPE: 2,
  POST_TEXT: 3,
  STATUS: 4,
  THREADS_ID: 5,
  PARENT_THREADS_ID: 6,
  CREATED_AT: 7,
  ERROR_MSG: 8,
};

const SHEET_NAME = "投稿予約";
const LOG_SHEET_NAME = "実行ログ";
const DRY_RUN = false; // テスト時は true に
