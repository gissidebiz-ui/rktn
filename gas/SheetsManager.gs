/**
 * ============================================================
 * SheetsManager.gs — スプレッドシート管理モジュール
 * ============================================================
 * SpreadsheetApp を使用して、投稿予約の書き込み・ステータス管理・
 * ログ記録を行います。
 *
 * シート構成:
 *   「投稿予約」シート — 投稿の予約・実行状態管理
 *   「実行ログ」シート — 実行結果の履歴
 * ============================================================
 */

/**
 * アクティブなスプレッドシートを取得する
 * @returns {Spreadsheet}
 */
function getSpreadsheet() {
  return SpreadsheetApp.getActiveSpreadsheet();
}

/**
 * 指定名のシートを取得（存在しない場合は作成）
 * @param {string} sheetName - シート名
 * @returns {Sheet}
 */
function getOrCreateSheet(sheetName) {
  const ss = getSpreadsheet();
  let sheet = ss.getSheetByName(sheetName);

  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
    Logger.log(`[SheetsManager] シート「${sheetName}」を新規作成しました`);

    if (sheetName === SHEET_NAME) {
      // 投稿予約シートのヘッダーを追加
      sheet
        .getRange(1, 1, 1, 8)
        .setValues([
          [
            "予定時刻",
            "投稿タイプ",
            "投稿本文",
            "ステータス",
            "Threads ID",
            "親Threads ID",
            "作成日時",
            "エラー",
          ],
        ]);
      sheet.getRange(1, 1, 1, 8).setFontWeight("bold");
      sheet.setFrozenRows(1);

      // 列幅を調整
      sheet.setColumnWidth(1, 140); // 予定時刻
      sheet.setColumnWidth(2, 100); // 投稿タイプ
      sheet.setColumnWidth(3, 400); // 投稿本文
      sheet.setColumnWidth(4, 80); // ステータス
      sheet.setColumnWidth(5, 150); // Threads ID
      sheet.setColumnWidth(6, 150); // 親Threads ID
      sheet.setColumnWidth(7, 140); // 作成日時
      sheet.setColumnWidth(8, 200); // エラー

      // 分析用カラム
      sheet
        .getRange(1, 9, 1, 6)
        .setValues([
          [
            "いいね数",
            "返信数",
            "再投稿数",
            "引用数",
            "表示数",
            "最終分析日時",
          ],
        ]);
      sheet.getRange(1, 9, 1, 6).setFontWeight("bold");
      for (let c = 9; c <= 14; c++) {
        sheet.setColumnWidth(c, 80);
      }
    }

    if (sheetName === LOG_SHEET_NAME) {
      // 実行ログシートのヘッダー
      sheet
        .getRange(1, 1, 1, 4)
        .setValues([["実行日時", "アクション", "結果", "詳細"]]);
      sheet.getRange(1, 1, 1, 4).setFontWeight("bold");
      sheet.setFrozenRows(1);
    }
  }

  return sheet;
}

/**
 * 投稿予約シートの初期化（高速版）
 */
function clearPendingPosts() {
  const sheet = getOrCreateSheet(SHEET_NAME);
  const lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    try {
      sheet.deleteRows(2, lastRow - 1);
      SpreadsheetApp.flush();
      Logger.log(`[SheetsManager] ${lastRow - 1}件の予約をクリアしました`);
    } catch (e) {
      sheet.getRange(2, 1, lastRow, sheet.getLastColumn()).clearContent();
      Logger.log(
        `[SheetsManager] 行削除エラー (フォールバック実行): ${e.message}`,
      );
    }
  } else {
    Logger.log("[SheetsManager] 初期化不要（データなし）");
  }
}

/**
 * 予約情報を一括書き出し
 */
function writePendingPosts(posts) {
  const sheet = getOrCreateSheet(SHEET_NAME);
  const rows = posts.map((p) => {
    const row = new Array(Object.keys(SHEET_COLUMNS).length).fill("");
    row[SHEET_COLUMNS.SCHEDULED_TIME - 1] = p.scheduledTime;
    row[SHEET_COLUMNS.POST_TYPE - 1] = p.type;
    row[SHEET_COLUMNS.POST_TEXT - 1] = p.text;
    row[SHEET_COLUMNS.STATUS - 1] = "pending";
    row[SHEET_COLUMNS.CREATED_AT - 1] = new Date();
    return row;
  });
  if (rows.length > 0) {
    sheet
      .getRange(sheet.getLastRow() + 1, 1, rows.length, rows[0].length)
      .setValues(rows);
    Logger.log(`[SheetsManager] ${rows.length}件の予約を書き込みました`);
  }
}

/**
 * 日付文字列またはDateオブジェクトを確実にDateオブジェクトに変換
 */
function parseDate(val) {
  if (val instanceof Date) return val;
  if (typeof val === "string") {
    // yyyy/MM/dd HH:mm 形式をサポート
    return new Date(val.replace(/-/g, "/"));
  }
  return new Date(val);
}

/**
 * 次に投稿すべき「単一の投稿」を取得
 */
function getNextPendingPost() {
  const sheet = getOrCreateSheet(SHEET_NAME);
  const data = sheet.getDataRange().getValues();
  const now = new Date();

  for (let i = 1; i < data.length; i++) {
    const status = data[i][SHEET_COLUMNS.STATUS - 1];
    if (status !== "pending" && status !== "posting") continue;

    const sched = parseDate(data[i][SHEET_COLUMNS.SCHEDULED_TIME - 1]);
    if (sched <= now && shouldPostNow()) {
      let parentId = "";
      const type = data[i][SHEET_COLUMNS.POST_TYPE - 1];
      if (type === "affiliate_link" && i > 1) {
        // 直前のフック投稿のIDを取得
        // なぜ: 親（フック）が未投稿やエラーの場合、子だけ投稿すると文脈の壊れたスパムになるため防止する
        const parentStatus = data[i - 1][SHEET_COLUMNS.STATUS - 1];
        if (parentStatus !== "posted") {
          throw new Error("親投稿が未完了のため中止");
        }
        parentId = String(data[i - 1][SHEET_COLUMNS.TWEET_ID - 1] || "");
      }

      return {
        row: i + 1,
        type: type,
        text: data[i][SHEET_COLUMNS.POST_TEXT - 1],
        isThreadStart: i % 4 === 1, // 3:1 ループなら 2, 6, 10行目...が開始
        parentId: parentId,
      };
    }
  }
  return null;
}

/**
 * 次に投稿すべき「スレッドセット」を取得
 */
function getNextPendingPostSet() {
  const sheet = getOrCreateSheet(SHEET_NAME);
  const data = sheet.getDataRange().getValues();
  const now = new Date();
  const set = [];

  for (let i = 1; i < data.length; i++) {
    const status = data[i][SHEET_COLUMNS.STATUS - 1];
    if (status !== "pending" && status !== "posting") continue;

    const sched = parseDate(data[i][SHEET_COLUMNS.SCHEDULED_TIME - 1]);
    if (sched <= now && shouldPostNow()) {
      set.push({
        row: i + 1,
        type: data[i][SHEET_COLUMNS.POST_TYPE - 1],
        text: data[i][SHEET_COLUMNS.POST_TEXT - 1],
      });
      if (set.length >= 4) break;
    } else if (set.length > 0) {
      break;
    }
  }
  return set.length > 0 ? set : null;
}

/**
 * 投稿ステータスの一括更新
 */
function updatePostStatusBatch(results) {
  const sheet = getOrCreateSheet(SHEET_NAME);
  results.forEach((res) => {
    sheet
      .getRange(res.row, SHEET_COLUMNS.STATUS)
      .setValue(res.success ? "posted" : "error");

    if (res.success) {
      sheet.getRange(res.row, SHEET_COLUMNS.TWEET_ID).setValue(res.postId);
      if (res.parentId)
        sheet
          .getRange(res.row, SHEET_COLUMNS.PARENT_TWEET_ID)
          .setValue(res.parentId);
    } else {
      sheet.getRange(res.row, SHEET_COLUMNS.ERROR_MSG).setValue(res.error);
    }

    // ステータスに応じて背景色を変更
    const cell = sheet.getRange(res.row, SHEET_COLUMNS.STATUS);
    if (res.success) {
      cell.setBackground("#d4edda"); // 薄緑
    } else {
      cell.setBackground("#f8d7da"); // 薄赤
    }
  });
}

/**
 * 投稿のメトリクスを更新
 */
function updatePostMetrics(row, metrics) {
  const sheet = getOrCreateSheet(SHEET_NAME);
  if (!metrics) return;

  const values = [
    [
      metrics.likes || 0,
      metrics.replies || 0,
      metrics.reposts || 0,
      metrics.quotes || 0,
      metrics.views || 0,
      new Date(),
    ],
  ];

  sheet.getRange(row, SHEET_COLUMNS.METRICS_LIKES, 1, 6).setValues(values);
}

/**
 * 実行ログの書き込み
 */
function writeLog(action, status, message) {
  const sheet = getOrCreateSheet(LOG_SHEET_NAME);
  sheet.appendRow([new Date(), action, status, message]);
}

/**
 * 統計データの取得
 */
function getPostStats() {
  const sheet = getOrCreateSheet(SHEET_NAME);
  const data = sheet.getDataRange().getValues();
  const summary = { total: 0, pending: 0, posted: 0, error: 0 };
  for (let i = 1; i < data.length; i++) {
    // Start from 1 to skip header
    const status = data[i][SHEET_COLUMNS.STATUS - 1];
    summary.total++;
    if (summary[status] !== undefined) summary[status]++;
  }
  return summary;
}

// ================================
// テスト用関数
// ================================
function testSheetsManager() {
  // テスト用の投稿を書き込み
  const testPosts = [
    { type: "normal", text: "テスト通常投稿1", scheduledTime: new Date() },
    {
      type: "normal",
      text: "テスト通常投稿2",
      scheduledTime: new Date(Date.now() + 60 * 60000),
    },
    {
      type: "normal",
      text: "テスト通常投稿3",
      scheduledTime: new Date(Date.now() + 120 * 60000),
    },
    {
      type: "affiliate",
      text: "テストアフィ投稿 #PR",
      scheduledTime: new Date(Date.now() + 180 * 60000),
    },
  ];

  writePendingPosts(testPosts);

  const stats = getPostStats();
  Logger.log(`統計: ${JSON.stringify(stats)}`);

  const next = getNextPendingPost();
  Logger.log(`次の投稿: ${next ? next.text.substring(0, 30) : "なし"}`);
}
