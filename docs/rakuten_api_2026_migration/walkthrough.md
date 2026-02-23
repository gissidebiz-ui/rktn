# 楽天API 2026年仕様移行の修正内容確認

楽天アフィリエイトAPIの2026年仕様への移行が完了しました。

## 修正内容のまとめ

1. **Config.gs**:
   - `RAKUTEN_API_CONFIG` 定数を更新し、新ドメインおよび動的な Referer/Origin ゲッターを追加。
   - `RAKUTEN_ORIGIN` をスクリプトプロパティ `rakuten_origin` から取得するように修正（機密情報との一元管理）。
2. **secrets.yaml**:
   - `rakuten_access_key` を有効化。
   - `rakuten_origin` を追加し、API登録済みのアプリケーションURLを設定。
3. **src/make_input_csv.py**:
   - **エンドポイント変換ロジック**: 単純な置換ではなく、サービス別プレフィックス（`ichibams`, `ichibaranking`, `services`, `engine` 等）を正しく付与するロジックを実装。
   - **リファラ・オリジン**: `rakuten_origin` を優先的に Referer および Origin ヘッダーとして使用するように修正。
   - **バージョン更新**: 楽天市場ランキングのバージョンを `20220601` へ自動更新。
4. **PostGenerator.gs**:
   - **共通変換関数**: `convertToRakutenOpenApiUrl()` を追加し、Python側と同様のプレフィックス置換を実装。
   - **ヘッダー修正**: 送信時の Origin ヘッダーから末尾の `/` を除去（APIの厳格なチェックに対応）。

## 検証結果

- Python スクリプト (`make_input_csv.py`) を実行し、全アカウント・全ジャンル（市場、ブックス、トラベル）において正常にデータ取得（Status 200）ができることを確認しました。

## 動作確認のガイド

1. GASのスクリプトプロパティに `RAKUTEN_ACCESS_KEY` および `rakuten_origin` を設定してください。
2. `PostGenerator.gs` の `testPostGeneration()` を実行し、ログに取得した商品データが表示されることを確認してください。

## バックアップ

修正前のファイルは以下の場所にバックアップされています：
`backups/rakuten_migration_2026_0223/`
