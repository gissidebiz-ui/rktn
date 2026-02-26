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
 *    - GEMINI_API_KEY, RAKUTEN_APP_ID
 *    - TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
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
  get TWITTER_API_KEY() {
    return (
      PropertiesService.getScriptProperties().getProperty("TWITTER_API_KEY") ||
      ""
    );
  },
  get TWITTER_API_SECRET() {
    return (
      PropertiesService.getScriptProperties().getProperty(
        "TWITTER_API_SECRET",
      ) || ""
    );
  },
  get TWITTER_ACCESS_TOKEN() {
    return (
      PropertiesService.getScriptProperties().getProperty(
        "TWITTER_ACCESS_TOKEN",
      ) || ""
    );
  },
  get TWITTER_ACCESS_SECRET() {
    return (
      PropertiesService.getScriptProperties().getProperty(
        "TWITTER_ACCESS_SECRET",
      ) || ""
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
  get RAKUTEN_ACCESS_KEY() {
    return (
      PropertiesService.getScriptProperties().getProperty(
        "RAKUTEN_ACCESS_KEY",
      ) || ""
    );
  },
  get RAKUTEN_REFERER() {
    return (
      PropertiesService.getScriptProperties().getProperty("rakuten_origin") ||
      PropertiesService.getScriptProperties().getProperty("base_url") ||
      "https://gissidebiz-ui.github.io/rktn/html"
    );
  },
  get RAKUTEN_ORIGIN() {
    return (
      PropertiesService.getScriptProperties().getProperty("rakuten_origin") ||
      "https://gissidebiz-ui.github.io"
    );
  },
  get RAKUTEN_API_TYPE() {
    return (
      PropertiesService.getScriptProperties().getProperty("RAKUTEN_API_TYPE") ||
      "ichiba"
    );
  },
};

// ================================
// トレンド解析・ペルソナ設定
// ================================
const TREND_CONFIG = {
  // 【最重要】アカウントのペルソナ。
  get TARGET_DEMO() {
    return (
      PropertiesService.getScriptProperties().getProperty("TARGET_DEMO") ||
      "30代男性、ビジネスマン、効率化・最新ガジェット愛好家。等身大で有益な情報を発信するスタイル。一人称は「僕」で統一してください。"
    );
  },

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
  // ターゲットプラットフォーム ('threads' または 'twitter')
  // ※ ここを書き換えることで、文字数制限やプロンプトのトーンが自動で切り替わります
  PLATFORM: "twitter",

  get NORMAL_POST_MAX_CHARS() {
    return this.PLATFORM === "twitter" ? 130 : 500;
  },
  get AFFILIATE_POST_MIN_CHARS() {
    return this.PLATFORM === "twitter" ? 50 : 150;
  },
  get AFFILIATE_POST_MAX_CHARS() {
    return this.PLATFORM === "twitter" ? 100 : 500;
  },

  // 黄金比（通常 3 : アフィリエイト 1）
  NORMAL_POSTS_PER_SET: 3,
  AFFILIATE_POSTS_PER_SET: 1,
  TOTAL_POSTS_PER_SET: 4,

  // --- 分析・改善設定 ---
  ANALYZE_DAYS_BACK: 7, // 過去何日間の投稿を分析対象にするか
  HIGH_PERFORMANCE_LIMIT: 5, // 優秀な投稿として抽出する数

  get NORMAL_POST_STYLES() {
    const raw =
      PropertiesService.getScriptProperties().getProperty("NORMAL_POST_STYLES");
    return raw
      ? raw
          .split(",")
          .map(function (s) {
            return s.trim();
          })
          .filter(function (s) {
            return s !== "";
          })
      : [];
  },
};

// ================================
// 各種 API 内部設定
// ================================
const GEMINI_CONFIG = {
  MODEL: "gemini-2.0-flash",
  BASE_URL: "https://generativelanguage.googleapis.com/v1beta/models/",
  MAX_RETRIES: 7, // 429対策として増加（有料プラン考慮）
  RETRY_DELAY_MS: 2000,
  BASE_BACKOFF_MS: 4000, // 429エラー時の指数バックオフ基礎時間
};

// Threads API 設定（互換性のため残存）
// const THREADS_API_CONFIG = {
//   BASE_URL: "https://graph.threads.net/v1.0",
//   PUBLISH_WAIT_MS: 5000,
//   REPLY_DELAY_MS: 3000,
// };

const TWITTER_API_CONFIG = {
  TWEET_ENDPOINT: "https://api.twitter.com/2/tweets",
  POST_INTERVAL_MS: 3000, // 投稿間の待機時間（レート制限対策）
};

const RAKUTEN_API_CONFIG = {
  DOMAIN: "openapi.rakuten.co.jp",
  get REFERER() {
    return CONFIG.RAKUTEN_REFERER;
  },
  get ORIGIN() {
    return CONFIG.RAKUTEN_ORIGIN;
  },
};

const SHEET_COLUMNS = {
  SCHEDULED_TIME: 1,
  POST_TYPE: 2,
  POST_TEXT: 3,
  STATUS: 4,
  TWEET_ID: 5,
  PARENT_TWEET_ID: 6,
  CREATED_AT: 7,
  ERROR_MSG: 8,
  // --- 分析用カラム ---
  METRICS_LIKES: 9,
  METRICS_REPLIES: 10,
  METRICS_REPOSTS: 11,
  METRICS_QUOTES: 12,
  METRICS_VIEWS: 13,
  ANALYZED_AT: 14,
};

const SHEET_NAME = "投稿予約";
const LOG_SHEET_NAME = "実行ログ";
const DRY_RUN = false; // テスト時は true に
