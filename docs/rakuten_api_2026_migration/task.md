# 楽天API 2026年仕様移行タスク

- [x] 事前準備
  - [x] 修正ファイルのバックアップ作成（`backups/`）
- [ ] ドキュメント作成
  - [x] `task.md` の作成
  - [x] `implementation_plan.md` の作成
- [x] Phase 1: config ディレクトリ (および Config.gs)
  - [x] `secrets.yaml` の更新（`rakuten_origin` 追加）
  - [x] `Config.gs` の更新（Origin/Referer ゲッター追加、定数修正）
- [ ] Phase 2: src ディレクトリ
  - [ ] `make_input_csv.py` の新仕様対応（サービス別のプレフィックス置換ロジック実装）
- [ ] Phase 3: gas ディレクトリ
  - [ ] `PostGenerator.gs` の新仕様対応（サービス別のプレフィックス置換、ヘッダー修正）
- [x] 動作確認・検証
  - [x] `testPostGeneration()` による動作確認
  - [x] `walkthrough.md` の作成
