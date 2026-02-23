import os

# 生成される機密情報ファイルのテンプレート内容
TEMPLATE = """google_api_key: "YOUR_GOOGLE_API_KEY"
rakuten_application_id: "YOUR_RAKUTEN_APP_ID"
rakuten_affiliate_id: "YOUR_RAKUTEN_AFFILIATE_ID"
"""

def main():
    """機密情報 (secrets.yaml) のテンプレートファイルを生成します。"""
    secrets_path = "../config/secrets.yaml"

    # ファイルがすでに存在する場合は、誤って上書きしないよう保護
    if os.path.exists(secrets_path):
        print("secrets.yaml はすでに存在します。上書きしません。")
        return

    # config ディレクトリが無い場合は作成
    os.makedirs("../config", exist_ok=True)

    # テンプレートを書き込み
    with open(secrets_path, "w", encoding="utf-8") as f:
        f.write(TEMPLATE)

    print("secrets.yaml のテンプレートを生成しました → ../config/secrets.yaml")
    print("必要なキーを入力してください。")

if __name__ == "__main__":
    main()
