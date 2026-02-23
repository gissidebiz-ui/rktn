/**
 * ============================================================
 * PostGenerator.gs — 投稿生成モジュール（25%ルール）
 * ============================================================
 * トレンド解析結果を反映し、通常投稿3件＋アフィリエイト投稿1件の
 * 「4件セット」を生成します。Threads 特有のフォーマットを適用。
 * ============================================================
 */

/**
 * 楽天 API から商品情報を取得する
 * @param {string} keyword - 検索キーワード
 * @param {number} hits - 取得件数（デフォルト: 3）
 * @returns {Object[]} 商品情報の配列 [{name, url, price, reviewAvg, reviewCount, pointRate}]
 */
function fetchRakutenItems(keyword, hits) {
  hits = hits || 3;
  const appId = CONFIG.RAKUTEN_APP_ID;
  const affiliateId = CONFIG.RAKUTEN_AFFILIATE_ID;
  const accessKey = CONFIG.RAKUTEN_ACCESS_KEY;

  if (!appId || !accessKey) {
    throw new Error(
      "RAKUTEN_APP_ID または RAKUTEN_ACCESS_KEY がスクリプトプロパティに設定されていません",
    );
  }

  const rawUrl =
    `https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601` +
    `?applicationId=${appId}` +
    `&accessKey=${accessKey}` +
    `&affiliateId=${affiliateId}` +
    `&keyword=${encodeURIComponent(keyword)}` +
    `&hits=${hits}` +
    "&sort=-reviewCount" +
    "&availability=1";

  const url = convertToRakutenOpenApiUrl(rawUrl);

  const options = {
    method: "get",
    headers: {
      Referer: RAKUTEN_API_CONFIG.REFERER,
      Origin: RAKUTEN_API_CONFIG.ORIGIN.replace(/\/$/, ""),
    },
    muteHttpExceptions: true,
  };

  try {
    const response = UrlFetchApp.fetch(url, options);

    const data = JSON.parse(response.getContentText());

    if (!data.Items || data.Items.length === 0) {
      Logger.log(`[Rakuten] 商品が見つかりません: ${keyword}`);
      return [];
    }

    return data.Items.map(function (item) {
      const i = item.Item;
      return {
        name: i.itemName || "",
        url: i.affiliateUrl || i.itemUrl || "",
        price: String(i.itemPrice || ""),
        reviewAvg: String(i.reviewAverage || "0"),
        reviewCount: String(i.reviewCount || "0"),
        pointRate: String(i.pointRate || "1"),
        imageUrl:
          i.mediumImageUrls && i.mediumImageUrls[0]
            ? i.mediumImageUrls[0].imageUrl
            : "",
      };
    });
  } catch (e) {
    Logger.log(`[Rakuten] API エラー: ${e.message}`);
    return [];
  }
}

/**
 * 楽天 API URL を新仕様のエンドポイントに変換する
 */
function convertToRakutenOpenApiUrl(url) {
  const endpointMapping = {
    "IchibaItem/Search": "ichibams",
    "IchibaItem/Ranking": "ichibaranking",
    "BooksTotal/Search": "services",
    "BooksCD/Search": "services",
    "BooksDVD/Search": "services",
    "BooksGame/Search": "services",
    "BooksMagazine/Search": "services",
    "Travel/HotelRanking": "engine",
    "Travel/KeywordHotelSearch": "engine",
    "Travel/GetAreaClass": "engine",
  };

  let newUrl = url.replace("app.rakuten.co.jp", RAKUTEN_API_CONFIG.DOMAIN);

  // 楽天市場ランキングのバージョン更新 (20170628 -> 20220601)
  if (newUrl.indexOf("IchibaItem/Ranking/20170628") !== -1) {
    newUrl = newUrl.replace("20170628", "20220601");
  }

  for (let key in endpointMapping) {
    if (
      newUrl.indexOf(key) !== -1 &&
      newUrl.indexOf(endpointMapping[key] + "/api/") === -1
    ) {
      newUrl = newUrl.replace("services/api/", endpointMapping[key] + "/api/");
      break;
    }
  }
  return newUrl;
}

/**
 * 楽天 URL から直接商品情報を取得する（URL指定版）
 * @param {string} rakutenApiUrl - 楽天 API の完全な URL
 * @returns {Object[]} 商品情報の配列
 */
function fetchRakutenItemsByUrl(rakutenApiUrl) {
  const appId = CONFIG.RAKUTEN_APP_ID;
  const affiliateId = CONFIG.RAKUTEN_AFFILIATE_ID;

  // URL にアプリIDが含まれていなければ追加
  // 2026年新仕様に基づき、ドメインとパラメータを更新
  let url = convertToRakutenOpenApiUrl(rakutenApiUrl);

  if (url.indexOf("applicationId") === -1) {
    url += (url.indexOf("?") === -1 ? "?" : "&") + `applicationId=${appId}`;
  }
  if (url.indexOf("accessKey") === -1) {
    url += `&accessKey=${CONFIG.RAKUTEN_ACCESS_KEY}`;
  }
  if (url.indexOf("affiliateId") === -1 && affiliateId) {
    url += `&affiliateId=${affiliateId}`;
  }

  const options = {
    method: "get",
    headers: {
      Referer: RAKUTEN_API_CONFIG.REFERER,
      Origin: RAKUTEN_API_CONFIG.ORIGIN.replace(/\/$/, ""),
    },
    muteHttpExceptions: true,
  };

  try {
    const response = UrlFetchApp.fetch(url, options);

    const data = JSON.parse(response.getContentText());

    // 楽天 Books 系 API と Ichiba API で構造が異なるため両方に対応
    const items = data.Items || data.items || [];

    return items.map(function (item) {
      const i = item.Item || item;
      return {
        name: i.itemName || i.title || i.hotelName || "",
        url: i.affiliateUrl || i.itemUrl || i.hotelInformationUrl || "",
        price: String(i.itemPrice || i.salesPrice || i.hotelMinCharge || ""),
        reviewAvg: String(i.reviewAverage || "0"),
        reviewCount: String(i.reviewCount || "0"),
        pointRate: String(i.pointRate || "1"),
        imageUrl: "",
      };
    });
  } catch (e) {
    Logger.log(`[Rakuten] URL API エラー: ${e.message}`);
    return [];
  }
}

/**
 * 楽天 API URL から商品情報を取得するヘルパー関数
 * @param {string} rakutenApiUrl - 楽天 API の完全な URL
 * @returns {Object|null} 単一の商品情報、または null
 */
function getRakutenProductByUrl(rakutenApiUrl) {
  const products = fetchRakutenItemsByUrl(rakutenApiUrl);
  return products.length > 0 ? products[0] : null;
}

/**
 * 楽天キーワードで商品情報を検索するヘルパー関数
 * @param {string} keyword - 検索キーワード
 * @param {Object} trendData - トレンドデータ
 * @returns {Object|null} 単一の商品情報、または null
 */
function searchRakutenProduct(keyword, trendData) {
  let products = [];
  if (keyword) {
    const searchKeyword =
      trendData && trendData.keywords.length > 0
        ? keyword +
          " " +
          trendData.keywords[
            Math.floor(Math.random() * trendData.keywords.length)
          ]
        : keyword;
    products = fetchRakutenItems(searchKeyword, 3);
  }

  if (products.length === 0 && trendData && trendData.keywords.length > 0) {
    const fallbackKeyword =
      trendData.keywords[
        Math.floor(Math.random() * trendData.keywords.length)
      ] || "おすすめ 人気";
    products = fetchRakutenItems(fallbackKeyword, 3);
  } else if (products.length === 0) {
    products = fetchRakutenItems("おすすめ 人気", 3);
  }

  return products.length > 0
    ? products[Math.floor(Math.random() * products.length)]
    : null;
}

/**
 * 1セット（4件）の投稿を生成する
 */
function generatePostSet(keywordOrUrl, offset = 0) {
  const trendData = analyzeTrends();
  const trendContext = buildTrendContext(trendData);
  const posts = [];

  // 通常投稿を 3件生成
  for (let i = 0; i < POST_CONFIG.NORMAL_POSTS_PER_SET; i++) {
    Logger.log(
      `[PostGenerator] 通常投稿 ${i + 1}/${POST_CONFIG.NORMAL_POSTS_PER_SET} 生成中...`,
    );
    let postText = "";
    let retries = 0;
    while (!postText && retries < 3) {
      postText = generateNormalPost(trendData, offset + i);
      if (!postText) {
        Logger.log(
          `[PostGenerator] 通常投稿 ${i + 1} リトライ ${retries + 1}/3`,
        );
        Utilities.sleep(1000);
      }
      retries++;
    }
    posts.push({
      type: "normal",
      text: postText || `（通常投稿 ${i + 1} の生成に失敗しました）`,
      isThreadStart: i === 0,
    });
    Utilities.sleep(1500);
  }

  // アフィリエイト投稿を 1件生成
  Logger.log("[PostGenerator] アフィリエイト投稿スロットの生成...");
  let affPostText = "";
  try {
    const product =
      keywordOrUrl.indexOf("http") === 0
        ? getRakutenProductByUrl(keywordOrUrl)
        : searchRakutenProduct(keywordOrUrl, trendData);

    if (product) {
      let retries = 0;
      while (!affPostText && retries < 3) {
        affPostText = generateAffiliatePost(product, trendContext);
        if (!affPostText) {
          Logger.log(
            `[PostGenerator] アフィリエイト投稿リトライ ${retries + 1}/3`,
          );
          Utilities.sleep(1000);
        }
        retries++;
      }
      if (affPostText) {
        posts.push({
          type: "affiliate",
          text: affPostText,
          isThreadStart: false,
          productInfo: product,
        });
      }
    }
  } catch (e) {
    Logger.log(`[PostGenerator] アフィリエイト生成失敗: ${e.message}`);
  }

  // アフィリエイトが失敗した場合は通常投稿で埋めて構造を維持
  if (!affPostText) {
    Logger.log("[PostGenerator] フォールバック: 通常投稿を生成します");
    let fallbackText = "";
    let retries = 0;
    while (!fallbackText && retries < 3) {
      fallbackText = generateNormalPost(trendData, offset + 3); // 4件目のスタイル
      if (!fallbackText) {
        Logger.log(
          `[PostGenerator] フォールバック通常投稿リトライ ${retries + 1}/3`,
        );
        Utilities.sleep(1000);
      }
      retries++;
    }
    posts.push({
      type: "normal",
      text: fallbackText || "（代替通常投稿の生成に失敗しました）",
      isThreadStart: false,
    });
  }

  // 4件を超える場合は切り詰め（フォールバックの二重追加を防止）
  if (posts.length > POST_CONFIG.TOTAL_POSTS_PER_SET) {
    Logger.log(
      `[PostGenerator] 生成数が${POST_CONFIG.TOTAL_POSTS_PER_SET}件を超過(${posts.length}件)。切り詰めます`,
    );
    posts.length = POST_CONFIG.TOTAL_POSTS_PER_SET;
  }

  Logger.log(
    `[PostGenerator] 4件セット確定: [${posts.map((p) => p.type).join(", ")}]`,
  );
  return posts;
}

/**
 * 通常投稿を生成
 */
function generateNormalPost(trendData, offset) {
  const styles = [
    "共感・あるある（読者が「わかる」と頷く内容）",
    "有益な知恵袋（意外と知らないライフハック）",
    "失敗からの学び（親近感と教訓）",
    "時短・効率化テクニック（即実行できるコツ）",
    "マインドセット（前向きになれる考え方）",
    "ガジェット/アプリ紹介（使いこなし術）",
    "質問・アンケート型（リプライを促す構成）",
  ];
  const style = styles[offset % styles.length];
  const focusKeyword =
    trendData.keywords[Math.floor(Math.random() * trendData.keywords.length)] ||
    "生産性";
  const month = new Date().getMonth() + 1;

  const prompt = `あなたはThreadsで「${TREND_CONFIG.TARGET_DEMO}」層から絶大な支持を得ているインフルエンサーです。

【重要制約】
・「テーマ：」や「生産性：」などのタイトル・見出しは一切不要です。冒頭から本文を開始してください。
・「はい」「承知しました」などの会話文や前置きは厳禁です。
・現在は${month}月です。必ずこの時期に相応しい内容にしてください。
・投稿本文のみをそのまま出力してください。

【今回の指示】
・テーマ: 「${focusKeyword}」を自然な形で本文に組み込んでください。
・スタイル: 「${style}」
・ハッシュタグは2つまで。絵文字は控えめに（2つまで）。
・読者に寄り添う「等身大」のトーンで、${POST_CONFIG.NORMAL_POST_MAX_CHARS}文字以内で生成してください。
・最後に思わず返信したくなるような「問いかけ」を入れてください。
`;

  return cleanPostText(callGeminiAPI(prompt));
}

/**
 * アフィリエイト投稿を生成
 */
function generateAffiliatePost(product, trendContext) {
  const month = new Date().getMonth() + 1;
  const prompt = `あなたはThreadsで「${TREND_CONFIG.TARGET_DEMO}」層に向けて、本当に良いモノだけを勧めるキュレーターです。

【紹介商品】
・商品名: ${product.name}
・URL: ${product.url}

【文脈情報】
${trendContext}

【重要制約】
・現在は${month}月です。今の時期にこの商品が必要な理由を${month}月の季節感と絡めて書いてください。
・冒頭に商品の具体的な魅力を2〜3行で記述してください（商品説明不足は厳禁）。
・「PRであること」を隠さず、かつ自然なトーンで ${product.url} への誘導を行ってください。
・全体で${POST_CONFIG.AFFILIATE_POST_MIN_CHARS}文字以上にしてください。
・会話文、確認コメント、装飾（【 】などの多用）は不要です。本文のみ出力してください。
`;

  let text = "";
  for (let r = 0; r < 2; r++) {
    text = cleanPostText(callGeminiAPI(prompt));
    if (text.length >= POST_CONFIG.AFFILIATE_POST_MIN_CHARS) break;
    Utilities.sleep(1000);
  }

  if (text.indexOf("#PR") === -1) text += "\n\n#PR";
  if (text.indexOf(product.url) === -1) text += "\n\n" + product.url;

  return text;
}

/**
 * クリーニング
 */
function cleanPostText(text) {
  if (!text) return "";

  // AI の前置き・挨拶・命令文を除去（複数パターンに対応）
  let cleaned = text
    // 「承知いたしました」「はい、」「かしこまりました」系の前置き
    .replace(
      /^(はい[、。！!]?\s*|承知いたしました[。！!]?\s*|承知しました[。！!]?\s*|かしこまりました[。！!]?\s*|了解しました[。！!]?\s*)/i,
      "",
    )
    // 「以下に〜作成します/作成しました」系
    .replace(
      /^.*?(以下に|以下の|下記に).*?(作成します|作成しました|提案します|生成します|出力します)[。！!]?\s*/i,
      "",
    )
    // 「**Threads投稿文案**」「**投稿文**」等のマークダウン見出し
    .replace(/^\*{1,2}.*?(投稿文案|投稿文|Threads|文案).*?\*{1,2}\s*/gim, "")
    // 「---」区切り線
    .replace(/^-{3,}\s*/gm, "")
    // コードブロック
    .replace(/```[\s\S]*?```/g, "")
    // マークダウンの見出し（# ）
    .replace(/^#{1,6}\s+.*?\n/gm, "")
    // 末尾の定型句
    .replace(
      /(\n|^)\s*(いかがでしょうか[？?]?$|ぜひ参考に|以上です|お役に立てれば|ご参考に|何かあれば).*$/gm,
      "",
    )
    // エスケープされた改行
    .replace(/\\n/g, "\n")
    // 連続改行を2つまでに
    .replace(/\n{3,}/g, "\n\n")
    // テーマ名ラベルを削除
    .replace(
      /^.*?(テーマ|主題|productivity|話題|content|post|投稿文?案?)[:：]\s*/im,
      "",
    )
    // 冒頭の【タイトル】を削除
    .replace(/^【.*?】\s*/m, "")
    // 冒頭の空行を除去
    .replace(/^\s*\n+/, "")
    .trim();

  // プレースホルダ検知（[ ] や 〇〇 など）
  const placeholderPattern = /\[.*?\]|〇{2,}|○{2,}|◯{2,}|△{2,}/;
  if (
    placeholderPattern.test(cleaned) ||
    cleaned.includes("ブランド名") ||
    cleaned.includes("〇〇")
  ) {
    Logger.log("[PostGenerator] プレースホルダを検出したため破棄");
    return "";
  }

  return /[ぁ-んァ-ン一-龥]/.test(cleaned) ? cleaned : "";
}

// ================================
// テスト用関数
// ================================
function testPostGeneration() {
  const postSet = generatePostSet("おすすめ ライフハック");
  Logger.log("=== 生成された4件セット ===");
  postSet.forEach(function (post, i) {
    Logger.log(`--- 投稿 ${i + 1} (${post.type}) ---`);
    Logger.log(post.text);
    Logger.log("");
  });
}
