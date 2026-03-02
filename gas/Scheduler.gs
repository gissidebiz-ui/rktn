/**
 * ============================================================
 * Scheduler.gs — スケジューラモジュール
 * ============================================================
 * 深夜休止・ゴールデンタイム対応の可変間隔スケジューリング。
 * 0:00〜6:59 休止、20:00〜23:00 は45〜60分間隔（アフィ優先）、
 * その他は90〜120分間隔。
 * ============================================================
 */

/**
 * 指定の時刻が休止時間かどうか判定
 * @param {number} hour - 時（0〜23）
 * @returns {boolean}
 */
function isQuietHours(hour) {
  return (
    hour >= SCHEDULE_CONFIG.QUIET_HOURS_START &&
    hour < SCHEDULE_CONFIG.QUIET_HOURS_END
  );
}

/**
 * 指定の時刻がゴールデンタイムかどうか判定
 * @param {number} hour - 時（0〜23）
 * @returns {boolean}
 */
function isGoldenTime(hour) {
  return (
    hour >= SCHEDULE_CONFIG.GOLDEN_TIME_START &&
    hour < SCHEDULE_CONFIG.GOLDEN_TIME_END
  );
}

/**
 * min〜max の範囲でランダムな整数を返す
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * 次の投稿可能時刻を計算する
 * @param {Date} lastPostTime - 直前の投稿時刻
 * @returns {Date} 次の投稿時刻
 */
function getNextPostTime(lastPostTime) {
  const lastHour = lastPostTime.getHours();
  let intervalMin;

  if (isGoldenTime(lastHour)) {
    intervalMin = randomInt(
      SCHEDULE_CONFIG.GOLDEN_INTERVAL_MIN,
      SCHEDULE_CONFIG.GOLDEN_INTERVAL_MAX,
    );
  } else {
    intervalMin = randomInt(
      SCHEDULE_CONFIG.NORMAL_INTERVAL_MIN,
      SCHEDULE_CONFIG.NORMAL_INTERVAL_MAX,
    );
  }

  const nextTime = new Date(lastPostTime.getTime() + intervalMin * 60 * 1000);

  // 休止時間に入ってしまう場合は翌朝 7:00 にスキップ
  if (isQuietHours(nextTime.getHours())) {
    nextTime.setDate(
      nextTime.getDate() +
        (nextTime.getHours() < SCHEDULE_CONFIG.QUIET_HOURS_END ? 0 : 1),
    );
    nextTime.setHours(SCHEDULE_CONFIG.QUIET_HOURS_END, 0, 0, 0);
  }

  return nextTime;
}

/**
 * 投稿セットに日付を割り当てる（ピーク時間帯集中投下方式）
 *
 * 4セット（各4件）を以下の時間帯に1セットずつ配置する:
 *   第1セット: 07:00〜08:30（朝の通勤）
 *   第2セット: 11:30〜12:30（昼休み）
 *   第3セット: 17:30〜18:30（帰宅）
 *   第4セット: 20:30〜22:00（夜のゴールデン）
 *
 * セット内間隔:
 *   通常/アフィフック → 直前の投稿から15〜30分後
 *   アフィリンク（子）→ アフィフック（親）から1〜2分後
 *
 * @param {Object[]} postSet - 投稿オブジェクトの配列（最大16件 = 4セット×4件）
 * @param {Date} startTime - 日付の基準（オプション、省略時は今日）
 * @returns {Object[]} scheduledTime が付与された投稿配列
 */
function generateSchedule(postSet, startTime = null) {
  // 4つのピーク時間帯の定義（開始・終了を分換算で保持）
  const PEAK_WINDOWS = [
    { startMin: 7 * 60, endMin: 8 * 60 + 30 }, // 第1セット: 07:00〜08:30
    { startMin: 11 * 60 + 30, endMin: 12 * 60 + 30 }, // 第2セット: 11:30〜12:30
    { startMin: 17 * 60 + 30, endMin: 18 * 60 + 30 }, // 第3セット: 17:30〜18:30
    { startMin: 20 * 60 + 30, endMin: 22 * 60 }, // 第4セット: 20:30〜22:00
  ];

  const POSTS_PER_SET = 4; // 通常2 + アフィフック1 + アフィリンク1
  const INTRA_SET_INTERVAL_MIN = 15; // セット内の通常/フック間隔（分）最小
  const INTRA_SET_INTERVAL_MAX = 30; // セット内の通常/フック間隔（分）最大
  const AFFILIATE_LINK_DELAY_MIN = 1; // アフィリンク→フックからの遅延（分）最小
  const AFFILIATE_LINK_DELAY_MAX = 2; // アフィリンク→フックからの遅延（分）最大

  // 基準日を決定（時分秒をリセットして日付だけ使う）
  const baseDate = startTime ? new Date(startTime.getTime()) : new Date();
  baseDate.setHours(0, 0, 0, 0);

  const result = [];
  let lastScheduledTime = null;
  let currentPeakIndex = 0;

  for (let i = 0; i < postSet.length; i++) {
    const post = postSet[i];
    const posInSet = i % POSTS_PER_SET; // セット内での位置 (0,1,2,3)

    // --- 1セット目の先頭（posInSet === 0）: 指定された時間枠内のランダム時刻 ---
    if (posInSet === 0) {
      const peakIndex = Math.min(
        Math.floor(i / POSTS_PER_SET),
        PEAK_WINDOWS.length - 1,
      );
      const peak = PEAK_WINDOWS[peakIndex];
      const randomMinuteOfDay = randomInt(peak.startMin, peak.endMin);

      const scheduledTime = new Date(baseDate.getTime());
      scheduledTime.setHours(0, randomMinuteOfDay, 0, 0);

      lastScheduledTime = scheduledTime;
      result.push({
        ...post,
        scheduledTime: Utilities.formatDate(
          scheduledTime,
          "Asia/Tokyo",
          "yyyy/MM/dd HH:mm",
        ),
      });

      currentPeakIndex = peakIndex + 1;
      Logger.log(
        `[Scheduler] 第${currentPeakIndex}セット 開始: ${Utilities.formatDate(scheduledTime, "Asia/Tokyo", "HH:mm")}`,
      );
      continue;
    }

    // --- アフィリンク（子）投稿: 直前のフック（親）から1〜2分後 ---
    if (post.type === "affiliate_link") {
      const delayMin = randomInt(
        AFFILIATE_LINK_DELAY_MIN,
        AFFILIATE_LINK_DELAY_MAX,
      );
      const scheduledTime = new Date(
        lastScheduledTime.getTime() + delayMin * 60 * 1000,
      );
      result.push({
        ...post,
        scheduledTime: Utilities.formatDate(
          scheduledTime,
          "Asia/Tokyo",
          "yyyy/MM/dd HH:mm",
        ),
      });
      // アフィリンクの時刻は次の投稿(もしあれば)の基準としないため、
      // lastScheduledTimeは更新せずフック（親）の時刻を維持します
      continue;
    }

    // --- 同一セット内の「次の通常投稿」や「アフィフック投稿」: 前の投稿から15〜30分後 ---
    const intervalMin = randomInt(
      INTRA_SET_INTERVAL_MIN,
      INTRA_SET_INTERVAL_MAX,
    );
    const scheduledTime = new Date(
      lastScheduledTime.getTime() + intervalMin * 60 * 1000,
    );
    lastScheduledTime = scheduledTime;

    result.push({
      ...post,
      scheduledTime: Utilities.formatDate(
        scheduledTime,
        "Asia/Tokyo",
        "yyyy/MM/dd HH:mm",
      ),
    });
  }

  Logger.log(
    `[Scheduler] スケジュール生成完了: ${result.length}件 (${currentPeakIndex}セット)`,
  );
  return result;
}

/**
 * 初回の開始時間を取得（現在時刻または翌朝）
 */
function getInitialStartTime() {
  const now = new Date();
  const currentHour = now.getHours();

  // 現在が休止時間中（24時〜7時）なら、今日の朝7時を開始にする
  if (currentHour < SCHEDULE_CONFIG.QUIET_HOURS_END) {
    const start = new Date(now.getTime());
    start.setHours(SCHEDULE_CONFIG.QUIET_HOURS_END, 0, 0, 0);
    return start;
  }

  // 現在が稼働時間中なら、現在時刻から開始する
  // (ただし、即座に投稿されるのを避けるため、5分程度のバッファを持たせても良い)
  const startWithBuffer = new Date(now.getTime() + 5 * 60 * 1000);
  return startWithBuffer;
}

/**
 * 現在が投稿可能な時間帯かチェック
 */
function shouldPostNow() {
  const now = new Date();
  const hour = now.getHours();
  // 7時〜24時（0時）の間を稼働時間とする
  return hour >= SCHEDULE_CONFIG.QUIET_HOURS_END && hour < 24;
}

/**
 * 現在時刻がアフィリエイト投稿に適しているか判定
 * @returns {boolean}
 */
function isAffiliateOptimalTime() {
  const hour = new Date().getHours();
  return isGoldenTime(hour);
}

// ================================
// テスト用関数
// ================================
function testScheduler() {
  // テスト用の4件セットを模擬
  const mockPostSet = [
    { type: "normal", text: "通常投稿1", scheduledTime: null },
    { type: "normal", text: "通常投稿2", scheduledTime: null },
    { type: "normal", text: "通常投稿3", scheduledTime: null },
    { type: "affiliate", text: "アフィ投稿", scheduledTime: null },
  ];

  const startTime = new Date();
  startTime.setHours(8, 0, 0, 0); // 朝8時開始を仮定

  const scheduled = generateSchedule(mockPostSet, startTime);
  Logger.log("=== スケジュール結果 ===");
  scheduled.forEach(function (post, i) {
    const timeStr = Utilities.formatDate(
      post.scheduledTime,
      "Asia/Tokyo",
      "HH:mm",
    );
    Logger.log(
      `${i + 1}. [${timeStr}] ${post.type}: ${post.text.substring(0, 30)}...`,
    );
  });

  Logger.log(`現在投稿可能: ${shouldPostNow()}`);
  Logger.log(`アフィリエイト最適時間: ${isAffiliateOptimalTime()}`);
}
