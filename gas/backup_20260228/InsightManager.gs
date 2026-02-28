/**
 * ============================================================
 * InsightManager.gs — インサイト分析マネージャー
 * ============================================================
 * 投稿済みのスレッドから定期的にインサイトを取得し、
 * スプレッドシートを更新します。
 * ============================================================
 */

/**
 * 過去の投稿のインサイトを更新する
 */
function refreshRecentPostInsights() {
  Logger.log("[InsightManager] インサイト更新開始...");
  const sheet = getOrCreateSheet(SHEET_NAME);
  const data = sheet.getDataRange().getValues();
  const now = new Date();
  const cutoffDate = new Date(
    now.getTime() - POST_CONFIG.ANALYZE_DAYS_BACK * 24 * 60 * 60 * 1000,
  );

  let updateCount = 0;

  // 1行目はヘッダーなので2行目から
  for (let i = 1; i < data.length; i++) {
    const status = data[i][SHEET_COLUMNS.STATUS - 1];
    const threadId = data[i][SHEET_COLUMNS.TWEET_ID - 1];
    const createdAt = data[i][SHEET_COLUMNS.CREATED_AT - 1];

    // 投稿済み、かつIDがあり、分析対象期間内のものを更新
    if (status === "posted" && threadId && createdAt >= cutoffDate) {
      Logger.log(
        `[InsightManager] インサイト取得中: Row ${i + 1}, ID: ${threadId}`,
      );
      const metrics = getMediaInsights(threadId);

      if (metrics) {
        updatePostMetrics(i + 1, metrics);
        updateCount++;
        // APIレート制限に配慮
        Utilities.sleep(1000);
      }
    }
  }

  Logger.log(
    `[InsightManager] インサイト更新完了: ${updateCount}件更新しました`,
  );
  writeLog("インサイト更新", "success", `${updateCount}件の投稿を分析しました`);
}
