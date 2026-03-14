# 日本の祝日対応の実装計画

## 目的
X/Threads投稿の生成時、土日だけでなく「日本の祝日」も休日として扱い、平日の仕事や通勤に関する内容（満員電車など）の出力が行われないよう改善する。

## タスク
- [ ] `Config.gs` に日本の祝日を判定するオプションを追加する
- [ ] Google Calendarの「日本の祝日」機能を利用し、特定の日付が祝日かどうかを判定する関数 `isHoliday(date)` を `PostGenerator.gs` などの適切な場所に実装する。
- [ ] `PostGenerator.gs` の `generateNormalPostsBatch` および `generateAffiliatePostPair` での `isWeekend` の判定条件に `isHoliday(date)` を追加し、休日のコンテキストを正しくAIプロンプトに反映させる。
- [ ] GASのテスト実行を通してプロンプトが正しく生成されているか確認する。
