import os
import csv
import requests  # type: ignore
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Tuple, Any
from di_container import get_container, DIContainer


class InputCSVGenerator:
    """依存性の注入 (DI) を利用した CSV 入力データ生成クラス。"""
    
    DEFAULT_ITEM_NUM: int = 5  # URLに hits 指定がない場合のデフォルト取得件数
    
    def __init__(self, container: DIContainer | None = None):
        """初期化。DI コンテナをオプションで指定可能です。
        
        Args:
            container: DI コンテナインスタンス（指定がない場合はグローバルなコンテナを使用）
        """
        self.container = container or get_container()
        self.accounts = self.container.get_accounts()
        self.secrets = self.container.get_secrets()        # APIキーなどの取得
        self.application_id = self.secrets.get("rakuten_application_id")
        self.access_key = self.secrets.get("rakuten_access_key")
        self.affiliate_id = self.secrets.get("rakuten_affiliate_id")
        # Referer/Origin は新仕様で必須。一元管理のため rakuten_origin を優先使用
        self.referer = self.secrets.get("rakuten_origin")
        self.origin = self.referer.rstrip("/")

    
    def remove_dup(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """取得したアイテムリストから重複を排除します。
        
        Args:
            items: アイテムのリスト
            
        Returns:
            重複排除後のアイテムリスト
        """
        seen = set()
        result = []

        for entry in items:
            # API の種類によって、情報の階層構造（'Item', 'Hotel', 'hotel', 'Ranking' 等）が異なります。
            item = entry.get("Item") or entry.get("Hotel") or entry.get("hotel") or entry.get("Ranking") or entry
            
            # 抽出対象がリストの場合（楽天トラベル KeywordSearch 等）の基本情報取得
            base_info = {}
            if isinstance(item, list):
                for sub in item:
                    if "hotelBasicInfo" in sub or "basicInfo" in sub:
                        base_info = sub.get("hotelBasicInfo") or sub.get("basicInfo")
                        break
            elif isinstance(item, dict) and "Ranking" in entry: # 楽天トラベルランキングの場合
                hotels = item.get("hotels", [])
                if hotels and isinstance(hotels, list):
                    h_item = hotels[0].get("hotel", {})
                    if isinstance(h_item, list):
                        for sub in h_item:
                            if "hotelBasicInfo" in sub or "basicInfo" in sub:
                                base_info = sub.get("hotelBasicInfo") or sub.get("basicInfo")
                                break
            else:
                base_info = item.get("hotelBasicInfo") or item.get("basicInfo") or item
            
            # 商品名またはホテル名をキーとして重複を判定
            title = base_info.get("hotelName") or base_info.get("itemName") or base_info.get("title", "")
            
            if title and title not in seen:
                seen.add(title)
                result.append(entry)
        return result

    def fetch_items(self, url: str, genre_name: str) -> List[Tuple[Any, ...]]:
        """指定された API URL からアイテム情報を取得します。
        
        Args:
            url: API リクエスト用 URL
            genre_name: ジャンル名（カテゴリ名）
            
        Returns:
            (タイトル, 商品URL, 画像URL, 価格, レビュー平均, レビュー数, ポイント倍率) のタプルのリスト
        """
        # 1. URL から 'hits' パラメータ（取得件数）を抽出
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # URL に &hits=10 等が指定されていればそれを使用し、なければデフォルト値 (5) を使用
        target_count = int(query_params.get('hits', [self.DEFAULT_ITEM_NUM])[0])

        # 2. API リクエストの実行
        # 2026年新仕様に基づき、ドメインとエンドポイントを更新
        # サービス種類に応じたプレフィックスを付与
        endpoint_mapping = {
            "IchibaItem/Search": "ichibams",
            "IchibaItem/Ranking": "ichibaranking", # Ranking は専用プレフィックス
            "BooksTotal/Search": "services",      # Books は services のまま
            "BooksCD/Search": "services",
            "BooksDVD/Search": "services",
            "BooksGame/Search": "services",
            "BooksMagazine/Search": "services",
            "Travel/HotelRanking": "engine",      # Travel は engine
            "Travel/KeywordHotelSearch": "engine",
            "Travel/GetAreaClass": "engine",
        }
        
        new_endpoint = url.replace("app.rakuten.co.jp", "openapi.rakuten.co.jp")
        
        # 楽天市場ランキングのバージョン更新 (20170628 -> 20220601)
        if "IchibaItem/Ranking/20170628" in new_endpoint:
            new_endpoint = new_endpoint.replace("20170628", "20220601")

        for old_path, prefix in endpoint_mapping.items():
            if old_path in new_endpoint and f"{prefix}/api/" not in new_endpoint:
                new_endpoint = new_endpoint.replace("services/api/", f"{prefix}/api/")
                break


        params = {
            "format": "json",
            "applicationId": self.application_id,
            "accessKey": self.access_key,
            "affiliateId": self.affiliate_id,
        }

        headers = {
            "Referer": self.referer,
            "Origin": self.origin
        }

        time.sleep(1)  # 短時間での連続アクセスによる API 負荷を軽減
        try:
            # 新仕様のエンドポイントとヘッダーを使用してリクエスト
            response = requests.get(new_endpoint, params=params, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"  [ERROR] Error Response: {response.text}")
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"  [ERROR] APIリクエスト失敗 ({new_endpoint}): {e}")

            # 旧仕様へのフォールバック（移行期間中のみ有効な可能性があるため、エラーログを残す）
            try:
                print(f"  [INFO] 旧エンドポイントで再試行します...")
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
            except Exception as e2:
                print(f"  [ERROR] 旧仕様再試行も失敗: {e2}")
                return []
        

        # 3. データの抽出（様々な API レスポンス構造に対応）
        raw_items = []
        if isinstance(data, dict):
            if "Items" in data:
                raw_items = data.get("Items", [])
            elif "items" in data:
                raw_items = data.get("items", [])
            if "Rankings" in data: # 楽天トラベルランキングAPI用
                for r in data.get("Rankings", []):
                    hotels = r.get("Ranking", {}).get("hotels", [])
                    raw_items.extend(hotels)
            elif "hotels" in data: # 楽天トラベルキーワード検索API用
                raw_items = data.get("hotels", [])
            elif "hits" in data and isinstance(data.get("hits"), list):
                raw_items = data.get("hits", [])
            elif "result" in data and isinstance(data.get("result"), dict) and "items" in data.get("result"):
                raw_items = data.get("result", {}).get("items", [])
            elif "data" in data and isinstance(data.get("data"), list):
                raw_items = data.get("data", [])
            else:
                if isinstance(data, list):
                    raw_items = data

        # 重複排除を実行
        unique_items = self.remove_dup(raw_items)

        results = []
        for entry in unique_items:
            # 指定された取得件数に達したら終了
            if len(results) >= target_count:
                break
                
            # 階層構造の解析
            if "Ranking" in entry:
                hotels_list = entry["Ranking"].get("hotels", [])
                if hotels_list and isinstance(hotels_list, list):
                    item_data = hotels_list[0].get("hotel", entry)
                else:
                    item_data = entry
            else:
                item_data = entry.get("hotel") or entry.get("Hotel") or entry.get("Item") or entry

            # リスト形式（トラベル等）または辞書形式からの情報抽出
            base_info = {}
            if isinstance(item_data, list):
                for sub in item_data:
                    if "hotelBasicInfo" in sub:
                        base_info = sub["hotelBasicInfo"]
                        break
                    elif "basicInfo" in sub:
                        base_info = sub["basicInfo"]
                        break
            else:
                base_info = item_data.get("hotelBasicInfo") or item_data.get("basicInfo") or item_data

            # 共通項目（タイトル、URL）の取得
            title = base_info.get("hotelName") or base_info.get("itemName") or base_info.get("title") or ""
            url_link = base_info.get("hotelInformationUrl") or base_info.get("affiliateUrl") or ""

            # --- 画像URLの取得（複数のキーパターンに対応） ---
            image_url = base_info.get("hotelImageUrl") or base_info.get("imageUrl") or ""
            if not image_url:
                medium_images = base_info.get("mediumImageUrls", [])
                if medium_images and isinstance(medium_images, list):
                    image_url = medium_images[0].get("imageUrl", "")
            
            if not image_url:
                images = item_data.get("images") or item_data.get("imageUrls") or []
                if isinstance(images, list) and images:
                    if isinstance(images[0], dict):
                        image_url = images[0].get("url") or images[0].get("imageUrl") or ""
                    else:
                        image_url = images[0]

            # --- 価格・レビュー・ポイント情報の取得 ---
            price = base_info.get("itemPrice") or base_info.get("hotelMinCharge") or base_info.get("price") or ""
            review_average = base_info.get("reviewAverage") or 0.0
            review_count = base_info.get("reviewCount") or 0
            point_rate = base_info.get("pointRate") or 1

            if title and url_link:
                results.append((title, url_link, image_url, price, review_average, review_count, point_rate))

        return results

    def generate(self) -> None:
        """全アカウントのジャンル設定に基づき、入力用 CSV を生成します。"""
        for account, data in self.accounts.items():
            genres = data.get("genres")

            # ジャンル設定がないアカウントはスキップ
            if not genres:
                print(f"\n=== {account} はジャンル設定がないためスキップ ===")
                continue

            print("\n" + "!" * 50)
            print(f"!!! アクセス中のアカウント: {account}")
            print(f"!!! 取得ジャンル: {list(genres.keys()) if genres else 'None'}")
            print("!" * 50 + "\n")
            account_items = []

            # ジャンル名とURLのペアをリスト化
            genre_tasks = list(genres.items())
            
            # APIの負荷制限を考慮し、アカウント内のジャンル取得を最大3並列で実行
            # (楽天APIの1秒に1リクエスト制限を尊重しつつスループットを上げる)
            with ThreadPoolExecutor(max_workers=3) as executor:

                # genre_name, url の順でタプルを受け取る fetch_items_wrapper を定義
                def fetch_items_wrapper(genre_info):
                    name, url = genre_info
                    print(f"  {name} を取得中… (URL: {url[:50]}...)")
                    # 各スレッド内で適度な待機を入れ、APIの密度を分散
                    time.sleep(0.5) 
                    return self.fetch_items(url, name)

                # 並列実行
                future_results = list(executor.map(fetch_items_wrapper, genre_tasks))
                
                for items in future_results:
                    print(f"    -> {len(items)}件取得しました")
                    account_items.extend(items)

            if not account_items:
                print(f"  [SKIP] 取得データが0件のため保存しません")
                continue

            # 保存パスの決定（src フォルダからの相対パスを解決）
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(script_dir, "..", "data", "input", f"{account}_input.csv")
            
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    for row in account_items:
                        writer.writerow(row)
                print(f"  [SUCCESS] {output_path} を生成（合計: {len(account_items)}件）")
            except Exception as e:
                print(f"  [ERROR] ファイル保存失敗: {e}")

        print("\nすべてのアカウントの CSV 生成処理が完了しました！")


def main() -> None:
    """メインエントリポイント。"""
    generator = InputCSVGenerator()
    generator.generate()


if __name__ == "__main__":
    main()
