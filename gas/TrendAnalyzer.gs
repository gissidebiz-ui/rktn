/**
 * ============================================================
 * TrendAnalyzer.gs — トレンド解析モジュール
 * ============================================================
 * Gemini API を活用し、CONFIG.TARGET_DEMO に基づいて
 * 現在バズっている話題や季節ネタを自律的に解析します。
 * ============================================================
 */

/**
 * Gemini API 呼び出し（汎用）
 */
function callGeminiAPI(prompt) {
  const url = `${GEMINI_CONFIG.BASE_URL}${GEMINI_CONFIG.MODEL}:generateContent?key=${CONFIG.GEMINI_API_KEY}`;
  const payload = {
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: { temperature: 0.9, maxOutputTokens: 2048 },
  };

  for (let attempt = 1; attempt <= GEMINI_CONFIG.MAX_RETRIES; attempt++) {
    try {
      const response = UrlFetchApp.fetch(url, {
        method: "post",
        contentType: "application/json",
        payload: JSON.stringify(payload),
        muteHttpExceptions: true,
      });
      const json = JSON.parse(response.getContentText());
      if (json.candidates && json.candidates[0]?.content?.parts[0]?.text) {
        return json.candidates[0].content.parts[0].text.trim();
      }
    } catch (e) {
      Logger.log(`[Gemini] リトライ ${attempt}: ${e.message}`);
      if (attempt < GEMINI_CONFIG.MAX_RETRIES)
        Utilities.sleep(GEMINI_CONFIG.RETRY_DELAY_MS);
    }
  }
  throw new Error("Gemini API の呼び出しに失敗しました。");
}

/**
 * トレンド解析の実行
 */
function analyzeTrends(forceRefresh = false) {
  const props = PropertiesService.getScriptProperties();
  if (!forceRefresh) {
    const cached = props.getProperty(TREND_CONFIG.CACHE_KEY);
    const cachedTs = props.getProperty(TREND_CONFIG.CACHE_TIMESTAMP_KEY);
    if (
      cached &&
      cachedTs &&
      Date.now() - parseInt(cachedTs) <
        TREND_CONFIG.CACHE_DURATION_HOURS * 3600000
    ) {
      return JSON.parse(cached);
    }
  }

  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth() + 1;
  const dateStr = Utilities.formatDate(now, "Asia/Tokyo", "yyyy年M月d日");

  const prompt = `あなたはSNSトレンドアナリストです。
今日は${dateStr}（${month}月）です。

■ 調査対象ペルソナ:
「${TREND_CONFIG.TARGET_DEMO}」

■ 依頼事項:
Threads上でこのペルソナに今刺さる「キーワード」と「テーマ」を抽出してください。
また、${month}月という季節に完全に合致した話題（${month}月ならではの悩み、イベント、準備）を3つ挙げてください。

【厳禁】${month}月と無関係な季節外れの話題（例: 2月に年末年始の話題など）は絶対に出さないでください。

■ 出力フォーマット（JSONのみ）:
{"keywords":["キーワード1","キーワード2",...],"themes":["テーマ1","テーマ2",...],"toneStyle":"推奨される語り口・トーン","seasonalTopics":["季節ネタ1","季節ネタ2",...]}
`;

  const rawText = callGeminiAPI(prompt);
  let trendData;
  try {
    const jsonStr = rawText.match(/\{[\s\S]*\}/)
      ? rawText.match(/\{[\s\S]*\}/)[0]
      : rawText;
    trendData = JSON.parse(jsonStr);
  } catch (e) {
    Logger.log("[TrendAnalyzer] パース失敗、デフォルトを使用");
    trendData = {
      keywords: ["時短術", "コスパ", "生産性向上"],
      themes: ["仕事効率化", "自己研鑽"],
      toneStyle: "共感を得やすい、柔らかくも理知的なトーン",
      seasonalTopics: [`${month}月の過ごし方`, "新生活の準備"],
    };
  }

  props.setProperty(TREND_CONFIG.CACHE_KEY, JSON.stringify(trendData));
  props.setProperty(TREND_CONFIG.CACHE_TIMESTAMP_KEY, String(Date.now()));
  return trendData;
}

/**
 * プロンプト用コンテキスト
 */
function buildTrendContext(trendData) {
  return `【最新トレンド・季節文脈】
・話題キーワード: ${trendData.keywords.join("、")}
・人気テーマ: ${trendData.themes.join("、")}
・季節の話題: ${trendData.seasonalTopics.join("、")}
・推奨スタイル: ${trendData.toneStyle}`.trim();
}
