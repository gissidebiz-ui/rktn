/**
 * ============================================================
 * TestRunner.gs — TDD用 簡易テストフレームワーク
 * ============================================================
 * GAS環境で動作するシンプルなアサーション関数とテストランナーを提供します。
 * 問題があれば積極的にこのファイルにテストケースを追加します。
 * ============================================================
 */

function runAllUnitTests() {
  Logger.log("=== ユニットテスト 開始 ===");
  let passed = 0;
  let failed = 0;

  // テストケース群
  const tests = [
    testSchedulerLogic_NoReverseTime,
    testSchedulerLogic_ApproxOneHourInterval,
  ];

  tests.forEach((testFunc) => {
    try {
      testFunc();
      Logger.log(`✅ PASS: ${testFunc.name}`);
      passed++;
    } catch (e) {
      Logger.log(`❌ FAIL: ${testFunc.name} - ${e.message}`);
      failed++;
    }
  });

  Logger.log(`=== テスト結果: ${passed} Passed, ${failed} Failed ===`);
  if (failed > 0) {
    throw new Error(`テストが ${failed} 件失敗しました`);
  }
}

// ----------------------------------------
// アサーション関数群
// ----------------------------------------
function assertEqual(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(
      `${message || "値が一致しません"} (Actual: ${actual}, Expected: ${expected})`,
    );
  }
}

function assertTrue(condition, message) {
  if (!condition) {
    throw new Error(`${message || "条件が true ではありません"}`);
  }
}

// ----------------------------------------
// 個別テストケース
// ----------------------------------------

/**
 * [テスト] 約1時間ごとに投稿がスケジュールされることを確認する
 */
function testSchedulerLogic_ApproxOneHourInterval() {
  const mockPostSet = [
    { type: "normal", text: "通常1", scheduledTime: null },
    { type: "normal", text: "通常2", scheduledTime: null },
    { type: "affiliate_hook", text: "フック", scheduledTime: null },
    { type: "affiliate_link", text: "リンク", scheduledTime: null },
  ];

  const startTime = new Date(2026, 0, 1, 10, 0, 0); // 10:00開始を想定
  const scheduled = generateSchedule(mockPostSet, startTime);

  const toDate = (str) => new Date(str.replace(/-/g, "/"));
  const times = scheduled.map((p) => toDate(p.scheduledTime).getTime());

  // 1件目は開始時刻から少し（最大5分程度）後であることを確認
  const firstDiffMin = (times[0] - startTime.getTime()) / (60 * 1000);
  assertTrue(
    firstDiffMin >= 0 && firstDiffMin <= 5,
    `最初の投稿は開始時刻の直後(0〜5分以内)であること (実際: ${firstDiffMin}分後)`,
  );

  // 2件目は1件目から約60〜65分後
  const diff1to2 = (times[1] - times[0]) / (60 * 1000);
  assertTrue(
    diff1to2 >= 60 && diff1to2 <= 65,
    `2件目の投稿は1件目から60〜65分後であること (実際: ${diff1to2}分後)`,
  );

  // 3件目は2件目から約60〜65分後
  const diff2to3 = (times[2] - times[1]) / (60 * 1000);
  assertTrue(
    diff2to3 >= 60 && diff2to3 <= 65,
    `3件目(フック)の投稿は2件目から60〜65分後であること (実際: ${diff2to3}分後)`,
  );
}

/**
 * [テスト] フックとリンクの時間逆転がないことを確認する
 */
function testSchedulerLogic_NoReverseTime() {
  const mockPostSet = [
    { type: "normal", text: "通常1", scheduledTime: null },
    { type: "affiliate_hook", text: "フック", scheduledTime: null },
    { type: "affiliate_link", text: "リンク", scheduledTime: null },
    { type: "normal", text: "通常2", scheduledTime: null },
  ];

  const startTime = new Date(2026, 0, 1, 10, 0, 0); // 10:00開始を想定
  const scheduled = generateSchedule(mockPostSet, startTime);

  // parseDate は SheetsManagerのものを想定して再定義(テスト用)
  const toDate = (str) => new Date(str.replace(/-/g, "/"));

  const hookStr = scheduled.find(
    (p) => p.type === "affiliate_hook",
  ).scheduledTime;
  const linkStr = scheduled.find(
    (p) => p.type === "affiliate_link",
  ).scheduledTime;

  const hookTime = toDate(hookStr);
  const linkTime = toDate(linkStr);

  assertTrue(
    hookTime.getTime() < linkTime.getTime(),
    `リンク時間(${linkStr}) は フック時間(${hookStr}) より後でなければならない`,
  );

  // さらに、1〜2分の差に収まっているかを確認
  const diffMinutes = (linkTime.getTime() - hookTime.getTime()) / (60 * 1000);
  assertTrue(
    diffMinutes >= 1 && diffMinutes <= 2,
    `フックとリンクの差は1〜2分であること (実際: ${diffMinutes}分)`,
  );
}
