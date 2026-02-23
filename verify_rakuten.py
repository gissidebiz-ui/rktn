import requests
import yaml

def check_rakuten():
    config_path = "config/secrets.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        secrets = yaml.safe_load(f)
    
    app_id = secrets.get("rakuten_application_id")
    access_key = secrets.get("rakuten_access_key")
    affiliate_id = secrets.get("rakuten_affiliate_id")
    referer = secrets.get("rakuten_origin")
    origin = referer.rstrip("/")

    tests = [
        ("Ichiba/Search/ichibams", "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601", {"keyword": "楽天"}),
        ("Ichiba/Ranking/ichibaranking", "https://openapi.rakuten.co.jp/ichibaranking/api/IchibaItem/Ranking/20220601", {"genreId": 0}),
        ("Books/Search/services", "https://openapi.rakuten.co.jp/services/api/BooksTotal/Search/20170404", {"keyword": "楽天"}),
        ("Travel/Ranking/engine", "https://openapi.rakuten.co.jp/engine/api/Travel/HotelRanking/20170426", {"hits": 1}),
        ("Travel/Keyword/engine", "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20170426", {"keyword": "USJ"}),
    ]
    
    headers = {
        "Referer": referer,
        "Origin": origin
    }
    
    import time
    for name, url, extra_params in tests:
        print(f"--- Testing {name} ---")
        time.sleep(1.5) # Wait for rate limit
        params = {
            "format": "json",
            "applicationId": app_id,
            "accessKey": access_key,
            "affiliateId": affiliate_id,
            "hits": 1
        }
        params.update(extra_params)
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=5)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Success!")
            else:
                print(f"Error: {response.text[:100]}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    check_rakuten()
