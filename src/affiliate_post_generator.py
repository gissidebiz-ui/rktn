import os
import csv
import glob
import time
import random
import subprocess
import re
import logging
from datetime import datetime
from typing import Dict, List, Any
from di_container import get_container, DIContainer
from ai_helpers import generate_with_retry
from html_generator import generate_short_url
from concurrent.futures import ThreadPoolExecutor


class AffiliatePostGenerator:
    """依存性の注入 (DI) を利用してアフィリエイトポストを生成するクラス。"""
    
    def __init__(self, container: DIContainer | None = None):
        """初期化。DI コンテナをオプションで指定可能です。
        
        Args:
            container: DI コンテナインスタンス（指定がない場合はグローバルなコンテナを使用）
        """
        self.container = container or get_container()
        self.config = self.container.get_generation_policy()
        self.accounts = self.container.get_accounts()
        self.client = self.container.get_ai_client()
        self.logger: logging.Logger = self.container.get_logger(__name__)
    
    def cleanup_html(self) -> None:
        """保持ポリシーに基づいて古い HTML ファイルを削除します。"""
        # スクリプトの場所基準で html ディレクトリの絶対パスを特定
        script_dir = os.path.dirname(os.path.abspath(__file__))
        html_dir = os.path.join(script_dir, "..", "html")
        
        # ディレクトリが存在しない場合はログを出力して終了
        if not os.path.exists(html_dir):
            self.logger.warning(f"HTML ディレクトリが見つかりません: {html_dir}")
            return

        now = time.time()
        
        # 設定ファイルから保持設定を取得（デフォルトは5日間）
        html_config = self.config.get("html_cleanup", {})
        retention_days = self.config.get("affiliate_post_generation", {}).get("html_retention_days", 5)
        seconds_in_retention = retention_days * 24 * 60 * 60
        
        # 削除対象から除外するファイル名と、対象とする拡張子
        excluded_files = html_config.get("excluded_files", ["index.html"])
        extensions = html_config.get("default_extensions", [".html"])

        html_files = []
        for f in os.listdir(html_dir):
            if f in excluded_files or not any(f.endswith(ext) for ext in extensions):
                continue
            file_path = os.path.join(html_dir, f)
            try:
                # 最終更新日時を取得
                mtime = os.path.getmtime(file_path)
                html_files.append({"name": f, "path": file_path, "mtime": mtime})
            except Exception:
                continue

        if not html_files:
            return

        # 最新のファイル（今回の実行で生成されたと思われるもの）を特定
        latest_file = max(html_files, key=lambda x: x["mtime"])
        latest_mtime = latest_file["mtime"]
        
        # 「最新セット」の基準: 最新ファイルから 10 分以内に更新されたものは残す
        SET_THRESHOLD_SECONDS = 10 * 60 
        
        # 本日の日付文字列
        today_str = datetime.now().strftime("%Y-%m-%d")

        for item in html_files:
            f = item["name"]
            file_path = item["path"]
            file_mtime = item["mtime"]
            
            # 判定1: 保持期間を過ぎているか（古いファイル）
            is_expired = (now - file_mtime > seconds_in_retention)
            
            # 判定2: 本日分だが、最新の実行セットではないか（同日内の古い実行残り）
            file_date_str = datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d")
            is_today = (file_date_str == today_str)
            is_old_today_set = is_today and (latest_mtime - file_mtime > SET_THRESHOLD_SECONDS)

            if is_expired or is_old_today_set:
                try:
                    os.remove(file_path)
                    reason = "保持期間超過" if is_expired else "当日内の古いセット"
                    print(f"削除しました: {f} ({reason})")
                    self.logger.info(f"HTML ファイルを削除しました: {f} ({reason})")
                except Exception as e:
                    print(f"削除失敗: {f} - {e}")
                    self.logger.warning(f"HTML ファイルの削除に失敗しました: {f} - {e}")

    def generate_post_text(self, product_name: str, short_url: str, price: str = "", review_average: str = "0.0", review_count: str = "0", point_rate: str = "1") -> str:
        """追加情報を活用して、より魅力的なアフィリエイト用ポスト文案を生成します。
        
        Args:
            product_name: 商品名
            short_url: 短縮風のリダイレクト URL
            price: 価格情報
            review_average: レビュー平均点
            review_count: レビュー件数
            point_rate: ポイント倍率
            
        Returns:
            生成されたポスト文案
        """
        # 商品名が長すぎる場合はカット
        max_name_len = self.config["affiliate_post_generation"].get("max_product_name_length", 80)
        safe_name = product_name[:max_name_len]

        # 追加情報のサマリを作成
        info_summary = []
        if price:
            info_summary.append(f"価格: {price}円")
        if float(review_average) > 0:
            info_summary.append(f"評価: ★{review_average}（{review_count}件）")
        if int(point_rate) > 1:
            info_summary.append(f"ポイント: {point_rate}倍")
        
        extra_info_text = " / ".join(info_summary)

        prompt = f"""
以下の情報から、X（旧Twitter）向けの「思わずクリックしたくなる」魅力的な投稿文を作成してください。
※文章の中にURLや[短縮URL]のようなプレースホルダは含めず、代わりに改行が必要な箇所には \n を入れてください。

【商品名】
{safe_name}

【補足情報】
{extra_info_text}

条件：
・本文は50文字以内
・価格、高評価、ポイント還元などの「お得感・安心感」を1つ以上盛り込む
・宣伝臭を抑えつつ、利用者のメリット（「これいい！」「助かる」等）を強調
・絵文字は1つまで
・短縮URLはシステムの最後に自動付与されるため、生成文には含めない
・1行で完結（改行が必要な場合は \n を使用し、実際の改行はしない）
"""
        text = generate_with_retry(self.client, prompt, self.config["affiliate_post_generation"])
        
        # ===== Step 1: 改行をリテラル形式に統一（行ずれ防止の最重要対策） =====
        # AI が実際の改行を返すことがあるため、最初にすべてリテラル \\n に変換
        text = text.replace("\r\n", "\\n").replace("\n", "\\n")
        
        # ===== Step 2: URL やプレースホルダの排除 =====
        text = re.sub(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+', '', text)
        text = text.replace("[短縮URL]", "\\n").replace("【短縮URL】", "\\n")
        
        # ===== Step 3: 不要な文字列（ノイズ）の除去 =====
        text = re.sub(r'^【.*?】', '', text)
        text = re.sub(r'^例[1-9]：', '', text)
        text = re.sub(r'^例：', '', text)
        text = text.replace("本文：", "").replace("投稿内容：", "")
        text = re.sub(r'上記例を参考にして.*', '', text)
        text = re.sub(r'他に\d+パターン.*', '', text)
        
        # ===== Step 4: \\n のノーマライズ（重複排除） =====
        # \\n が3つ以上連続する場合を \\n\\n に圧縮
        while "\\n\\n\\n" in text:
            text = text.replace("\\n\\n\\n", "\\n\\n")
        # 先頭・末尾の \\n を除去
        while text.startswith("\\n"):
            text = text[2:]
        while text.endswith("\\n"):
            text = text[:-2]
        text = text.strip()
        
        # ===== Step 5: プレースホルダ / テンプレート用単語の検知 =====
        placeholder_pattern = r'\[.*?\]|【.*?】|〇{2,}|○{2,}|◯{2,}|[X]{2,}|[x]{2,}|[△]{2,}|[Δ]{2,}|[×]{2,}'
        template_words = ["ブランド名", "商品名", "店舗名", "会社名", "カテゴリー", "〇〇", "○○"]
        if re.search(placeholder_pattern, text) or any(w in text for w in template_words):
            return "[AIエラー] プレースホルダまたはテンプレート用単語が含まれています"
        
        # ===== Step 6: 外国語エラー判定 =====
        if not re.search(r'[ぁ-んァ-ン一-龥]', text):
             return "[AIエラー] 日本語が含まれていません"

        # ===== Step 7: ハッシュタグの前に改行を挿入 =====
        if "#" in text:
            text = text.replace(" #", "\\n#").replace("　#", "\\n#")
            text = re.sub(r'([^\\n])#', r'\1\\n#', text)

        # ===== Step 8: URL を結合（\\n を確実に挿入） =====
        return f"{text}\\n\\n{short_url}"

    def generate(self) -> None:
        """全アカウントのアフィリエイト投稿文を生成し、GitHub へプッシュします。"""
        self.logger.info("アフィリエイトポスト生成を開始します")
        # 前処理: 古い HTML のクリーンアップ
        self.cleanup_html()

        # data/input フォルダ内の全ての CSV を対象にループ
        input_files = glob.glob("../data/input/*_input.csv")
        self.logger.debug(f"{len(input_files)} 件の入力 CSV を検出しました")

        for input_path in input_files:
            filename = os.path.basename(input_path)
            account = filename.replace("_input.csv", "")
            self.logger.info(f"アカウント '{account}' を処理中")

            output_path = f"../data/output/{account}_affiliate_posts.txt"
            entries = []

            # 入力 CSV を読み込み、リダイレクト HTML を生成
            with open(input_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    try:
                        if len(row) < 3:
                            continue
                        product_name = row[0]
                        affiliate_url = row[1]
                        image_url = row[2]
                        price = row[3] if len(row) > 3 else ""
                        review_avg = row[4] if len(row) > 4 else "0.0"
                        review_cnt = row[5] if len(row) > 5 else "0"
                        point_rate = row[6] if len(row) > 6 else "1"

                        # OGP 対応 HTML を生成し、短縮 URL を取得（HTMLタイトルにも反映させる）
                        short_url = generate_short_url(
                            affiliate_url, 
                            product_name, 
                            image_url,
                            price=price,
                            review_average=review_avg,
                            point_rate=point_rate
                        )
                        entries.append({
                            "product_name": product_name,
                            "short_url": short_url,
                            "price": price,
                            "review_avg": review_avg,
                            "review_cnt": review_cnt,
                            "point_rate": point_rate,
                            "post": None
                        })
                    except Exception as e:
                        print(f"[ERROR] 行の処理に失敗しました: {row}")
                        import traceback
                        traceback.print_exc()
                        continue

            # 各商品に対して AI 投稿文を並列生成
            with ThreadPoolExecutor(max_workers=5) as executor:
                def process_entry(entry):
                    try:
                        return self.generate_post_text(
                            entry["product_name"], 
                            entry["short_url"],
                            price=entry["price"],
                            review_average=entry["review_avg"],
                            review_count=entry["review_cnt"],
                            point_rate=entry["point_rate"]
                        )
                    except Exception as ex:
                        self.logger.error(f"生成エラー: {entry['product_name']} - {ex}")
                        return "[AIエラー] 生成に失敗しました"

                # 並列実行して結果を格納
                posts = list(executor.map(process_entry, entries))
                for i, post in enumerate(posts):
                    entries[i]["post"] = post

            # 失敗（空文字等）したエントリの再試行処理
            def _is_failed(p: str | None) -> bool:
                if p is None:
                    return True
                s = str(p).strip()
                return s == "" or s.startswith("[AIエラー]")

            failed_idxs = [i for i, e in enumerate(entries) if _is_failed(e.get("post"))]
            if failed_idxs:
                retry_passes = self.config["affiliate_post_generation"].get("retry_passes", 3)
                for rp in range(1, retry_passes + 1):
                    print(f"[再試行パス {rp}/{retry_passes}] 失敗した生成の再実行中: {len(failed_idxs)} 件")
                    for idx in failed_idxs[:]:
                        e = entries[idx]
                        try:
                            new_post = self.generate_post_text(e["product_name"], e["short_url"])
                            if not _is_failed(new_post):
                                entries[idx]["post"] = new_post
                                failed_idxs.remove(idx)
                        except Exception as ex:
                            print(f"[ERROR] 再試行エラー: {e['product_name']}")

            # 投稿順をランダムに入れ替えて保存
            posts = [e.get("post") or "" for e in entries]
            random.shuffle(posts)
            with open(output_path, "w", encoding="utf-8") as f:
                for p in posts:
                    # 改行文字の二重エスケープ等を補正して保存
                    safe_post = p.replace("\\\\n", "\\n")
                    f.write(safe_post + "\n")

            print(f"{output_path} を作成しました！")

        # HTML ファイルを GitHub Pages 等で公開するため、Git プッシュを実行
        try:
            print("GitHub へ変更を送信中...")
            subprocess.run(["git", "add", "-A"], check=True)
            subprocess.run(["git", "commit", "-m", "AI auto post update"], check=True)
            subprocess.run(["git", "push"], check=True)
        except Exception as e:
            print(f"GitHub push エラー（無視して続行します）: {e}")

        print("全アカウントのアフィリエイト投稿文生成が完了しました！")


def main() -> None:
    """メインエントリポイント。"""
    generator = AffiliatePostGenerator()
    generator.generate()


if __name__ == "__main__":
    main()
