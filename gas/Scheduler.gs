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
 * 投稿セットに日付を割り当てる
 * @param {Object[]} postSet - 投稿オブジェクトの配列
 * @param {Date} startTime - 開始時間の基準（オプション）
 */
function generateSchedule(postSet, startTime = null) {
  const result = [];
  let baseTime = startTime
    ? new Date(startTime.getTime())
    : getInitialStartTime();

  postSet.forEach((post, index) => {
    // 次の投稿時間を 60分後として計算
    baseTime = new Date(baseTime.getTime() + 60 * 60 * 1000);

    // 夜間（24:00〜07:00）の場合は翌朝にスキップ
    if (
      baseTime.getHours() < SCHEDULE_CONFIG.QUIET_HOURS_END ||
      baseTime.getHours() >= 24
    ) {
      baseTime.setHours(SCHEDULE_CONFIG.QUIET_HOURS_END, 0, 0, 0);
      if (baseTime.getHours() >= 24) baseTime.setDate(baseTime.getDate() + 1);
    }

    // 0〜5分のランダムな揺らぎ（Jitter）を加算
    const jitterMs =
      Math.floor(Math.random() * (SCHEDULE_CONFIG.JITTER_MAX_MIN + 1)) *
      60 *
      1000;
    const scheduledTime = new Date(baseTime.getTime() + jitterMs);

    result.push({
      ...post,
      scheduledTime: Utilities.formatDate(
        scheduledTime,
        "Asia/Tokyo",
        "yyyy/MM/dd HH:mm",
      ),
    });
  });

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
