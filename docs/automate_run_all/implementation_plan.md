# 実装計画 - run_all.py の自動実行

`run_all.py` を自動的に実行するための仕組みを構築します。用途に合わせて「ローカル実行」と「クラウド実行」の2つの方法を提供します。

## 提案内容

### 案1: ローカル自動化 (Windows Task Scheduler)

ユーザーの現在のPC環境で、指定した時間に自動実行する方法です。

- **`run_all.bat` [NEW]**: Python環境を起動して `run_all.py` を実行するバッチファイル。
- **設定手順**: Windowsの「タスクスケジューラ」にこのバッチファイルを登録する手順を提供します。

### 案2: クラウド自動化 (GitHub Actions)

PCを起動していなくても、GitHubのサーバー上で定期実行する方法です。

- **`daily-run.yml` [NEW]**: GitHub Actions のワークフローファイル。毎日 1回（時間は調整可能）実行するように設定します。
- **注意**: GitHub の Secrets に `google_api_key` などの秘密情報を登録する必要があります。

---

## 変更内容

### [src/run_all.bat](file:///c:/Users/hax37/Documents/yusuke_doc/git/work/rktn/src/run_all.bat) [NEW]

```batch
@echo off
cd /d %~dp0
python run_all.py
pause
```

※自動実行時は `pause` を除くか、最小化状態で実行するように設定します。

### [.github/workflows/daily-run.yml](file:///c:/Users/hax37/Documents/yusuke_doc/git/work/rktn/.github/workflows/daily-run.yml) [NEW]

定期実行（cron）を設定し、必要な環境変数を用意します。

---

## 検証計画

- `run_all.bat` を手動で実行し、正常にパイプラインが完了することを確認します。
- GitHub Actions の `workflow_dispatch` を手動でトリガーし、エラーなく実行できるか確認します（Secrets設定が必要なため、手順のみ提示）。
