# 楽天API 2026年仕様移行の実装計画

楽天アフィリエイトAPIの2026年5月完全移行に伴う仕様変更（ドメイン、ヘッダー要件、認証パラメータ名）に対応します。

## 概要

従来の `app.rakuten.co.jp` エンドポイントを新仕様の `openapi.rakuten.co.jp` に変更し、セキュリティ強化によるリファラチェック（Referer/Originヘッダー）および認証パラメータ名（`applicationId` -> `accessKey`）の変更を適用します。

## 変更内容

### Phase 1: config ディレクトリ (および Config.gs)

設定情報の更新と一元管理の準備。

#### [MODIFY] [secrets.yaml](file:///c:/Users/hax37/Documents/yusuke_doc/git/work/rktn/config/secrets.yaml)

- `rakuten_origin` を追加し、登録済みオリジンを設定。
- `base_url` が Referer として正しく設定されているか確認。

#### [MODIFY] [Config.gs](file:///c:/Users/hax37/Documents/yusuke_doc/git/work/rktn/gas/Config.gs)

- `RAKUTEN_ORIGIN`, `RAKUTEN_REFERER` を取得するゲッターを追加。
- `RAKUTEN_API_CONFIG` でこれらを参照するように修正。

### Phase 2: src ディレクトリ

Python側のデータ取得処理を最新のパス仕様に合わせます。

#### [MODIFY] [make_input_csv.py](file:///c:/Users/hax37/Documents/yusuke_doc/git/work/rktn/src/make_input_csv.py)

- エンドポイントURLの置換ロジックを修正。単純なドメイン置換ではなく、API種類に応じたプレフィックス（`ichibams/api/`, `travelhr/api/` 等）を考慮する。
- `rakuten_origin` を読み込み、ヘッダーに使用する。

### Phase 3: gas ディレクトリ

GAS側のリアルタイム取得・生成処理を最新のパス仕様に合わせます。

#### [MODIFY] [PostGenerator.gs](file:///c:/Users/hax37/Documents/yusuke_doc/git/work/rktn/gas/PostGenerator.gs)

- `fetchRakutenItems`: 市場商品検索用の新エンドポイント（`ichibams/api/...`）を適用。
- `fetchRakutenItemsByUrl`: URLに応じたプレフィックス置換ロジックを実装。
- `UrlFetchApp.fetch` のヘッダーで、新しく定義した `RAKUTEN_ORIGIN` を参照。

---

## 修正後のイメージ（例）

```javascript
const options = {
  method: "get",
  headers: {
    Referer: RAKUTEN_API_CONFIG.REFERER,
    Origin: RAKUTEN_API_CONFIG.ORIGIN,
  },
  muteHttpExceptions: true,
};
const response = UrlFetchApp.fetch(newUrl, options);
```

---

## 検証プラン

### 自動テスト

GAS環境のため、ローカルでの自動テストは困難ですが、以下のテスト用関数を実行してログを確認します。

- `testPostGeneration()` を実行し、楽天APIからエラー（403/400）が出ずに商品が取得できているか確認する。

### 手動検証

1. GASエディタ上で `fetchRakutenItems` を直接呼び出し、返却されるJSONに商品が含まれているか確認。
2. 403 Forbidden が発生しないこと、および `accessKey` パラメータが正しく認識されていることを確認。
