/**
 * ============================================================
 * PostGenerator.gs — 投稿生成モジュール（25%ルール）
 * ============================================================
 * トレンド解析結果を反映し、通常投稿3件＋アフィリエイト投稿1件の
 * 「4件セット」を生成します。X（Twitter）の全角140文字制限に対応。
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

  // APIタイプ（ichiba, books, travel）に応じてURLとソートを切り替え
  const apiType = CONFIG.RAKUTEN_API_TYPE;
  let rawUrl = "";
  if (apiType === "books") {
    rawUrl =
      `https://app.rakuten.co.jp/services/api/BooksTotal/Search/20170404` +
      `?applicationId=${appId}` +
      `&accessKey=${accessKey}` +
      `&affiliateId=${affiliateId}` +
      `&keyword=${encodeURIComponent(keyword)}` +
      `&hits=${hits}` +
      "&sort=sales" +
      "&availability=1";
  } else if (apiType === "travel") {
    rawUrl =
      `https://app.rakuten.co.jp/services/api/Travel/KeywordHotelSearch/20170426` +
      `?applicationId=${appId}` +
      `&accessKey=${accessKey}` +
      `&affiliateId=${affiliateId}` +
      `&keyword=${encodeURIComponent(keyword)}` +
      `&hits=${hits}`;
  } else {
    rawUrl =
      `https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601` +
      `?applicationId=${appId}` +
      `&accessKey=${accessKey}` +
      `&affiliateId=${affiliateId}` +
      `&keyword=${encodeURIComponent(keyword)}` +
      `&hits=${hits}` +
      "&sort=-reviewCount" +
      "&availability=1";
  }

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
    Logger.log(`[Rakuten] ${apiType} 取得開始 URL: ` + url);
    const response = UrlFetchApp.fetch(url, options);
    const content = response.getContentText();

    if (response.getResponseCode() !== 200) {
      Logger.log(
        "[Rakuten] エラーレスポンス (" +
          response.getResponseCode() +
          "): " +
          content,
      );
      throw new Error("Rakuten API returned " + response.getResponseCode());
    }

    const data = JSON.parse(content);
    // 構造の差異に対応（Items, items, hotels）
    const items = data.Items || data.items || data.hotels || [];

    if (items.length === 0) {
      Logger.log(`[Rakuten] 商品/施設が見つかりません: ${keyword}`);
      return [];
    }

    return items.map(function (item) {
      // 楽天トラベルの構造（nested hotelBasicInfo）にも対応
      let i = item.Item || item;
      if (item.hotel && Array.isArray(item.hotel)) {
        // KeywordHotelSearch 等のレスポンス
        const basic = item.hotel.find((h) => h.hotelBasicInfo);
        i = basic ? basic.hotelBasicInfo : item.hotel[0];
      } else if (item.hotel) {
        i = item.hotel;
      }

      return {
        name: i.itemName || i.title || i.hotelName || "",
        url: i.affiliateUrl || i.itemUrl || i.hotelInformationUrl || "",
        price: String(i.itemPrice || i.salesPrice || i.hotelMinCharge || ""),
        reviewAvg: String(i.reviewAverage || "0"),
        reviewCount: String(i.reviewCount || "0"),
        pointRate: String(i.pointRate || "1"),
        caption: i.itemCaption || i.hotelSpecialFeatures || "",
        imageUrl:
          i.mediumImageUrls && i.mediumImageUrls[0]
            ? i.mediumImageUrls[0].imageUrl
            : i.hotelImageUrl || i.largeImageUrl || i.mediumImageUrl || "",
      };
    });
  } catch (e) {
    Logger.log("[Rakuten] API エラー詳細: " + e.message);
    throw e;
  }
}

/**
 * 楽天 API URL を新仕様のエンドポイントに変換する
 */
function convertToRakutenOpenApiUrl(url) {
  if (!url) return url;

  const targetDomain = "openapi.rakuten.co.jp";
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

  let newUrl = url.replace("app.rakuten.co.jp", targetDomain);

  // 楽天市場ランキングのバージョン更新 (20170628 -> 20220601)
  if (newUrl.indexOf("IchibaItem/Ranking/20170628") !== -1) {
    newUrl = newUrl.replace("20170628", "20220601");
  }

  for (let key in endpointMapping) {
    if (
      newUrl.indexOf(key) !== -1 &&
      newUrl.indexOf(endpointMapping[key] + "/api/") === -1
    ) {
      // 一部のAPIは初期状態で services/api/ を持っていないか、既に置換されている場合を考慮
      if (newUrl.indexOf("services/api/") !== -1) {
        newUrl = newUrl.replace(
          "services/api/",
          endpointMapping[key] + "/api/",
        );
      } else if (newUrl.indexOf("/api/") !== -1) {
        // services/api 以外（既にドメイン置換済み等）でもプレフィックスを付ける必要がある場合
        const parts = newUrl.split("/api/");
        if (parts[0].indexOf(endpointMapping[key]) === -1) {
          parts[0] = parts[0] + "/" + endpointMapping[key];
          newUrl = parts.join("/api/");
        }
      }
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
    Logger.log("[Rakuten] URL指定取得開始 URL: " + url);
    const response = UrlFetchApp.fetch(url, options);
    const content = response.getContentText();

    if (response.getResponseCode() !== 200) {
      Logger.log(
        "[Rakuten] URL指定エラー (" +
          response.getResponseCode() +
          "): " +
          content,
      );
      throw new Error(
        "Rakuten API URL fetch returned " + response.getResponseCode(),
      );
    }

    const data = JSON.parse(content);

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
        caption: i.itemCaption || "",
        imageUrl: "",
      };
    });
  } catch (e) {
    Logger.log("[Rakuten] URL API エラー詳細: " + e.message);
    throw e;
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
  const apiType = CONFIG.RAKUTEN_API_TYPE;
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
    products = fetchRakutenItems(searchKeyword, 5);
  }

  if (products.length === 0 && trendData && trendData.keywords.length > 0) {
    const fallbackKeyword =
      trendData.keywords[
        Math.floor(Math.random() * trendData.keywords.length)
      ] || "人気";
    products = fetchRakutenItems(fallbackKeyword, 5);
  }

  if (products.length === 0) {
    let finalFallback = "おすすめ 人気";
    if (apiType === "books") finalFallback = "ベストセラー";
    if (apiType === "travel") finalFallback = "人気 温泉 ホテル";
    products = fetchRakutenItems(finalFallback, 10);
  }

  return products.length > 0
    ? products[Math.floor(Math.random() * products.length)]
    : null;
}

/**
 * 高評価の過去投稿を取得する
 */
function getHighPerformingPosts(limit) {
  limit = limit || POST_CONFIG.HIGH_PERFORMANCE_LIMIT;
  const sheet = getOrCreateSheet(SHEET_NAME);
  const data = sheet.getDataRange().getValues();

  // いいね + 返信 + 再投稿 の合計でソート
  const posts = [];
  for (let i = 1; i < data.length; i++) {
    const status = data[i][SHEET_COLUMNS.STATUS - 1];
    if (status !== "posted") continue;

    const likes = Number(data[i][SHEET_COLUMNS.METRICS_LIKES - 1]) || 0;
    const replies = Number(data[i][SHEET_COLUMNS.METRICS_REPLIES - 1]) || 0;
    const reposts = Number(data[i][SHEET_COLUMNS.METRICS_REPOSTS - 1]) || 0;
    const score = likes + replies * 2 + reposts * 3; // 返信や再投稿を重く評価

    if (score > 0) {
      posts.push({
        text: data[i][SHEET_COLUMNS.POST_TEXT - 1],
        score: score,
      });
    }
  }

  // スコア降順でソートして上位を返す
  return posts.sort((a, b) => b.score - a.score).slice(0, limit);
}

/**
 * 成功例をベースにしたプロンプト用テキストを構築
 */
function buildSuccessfulPostsContext() {
  const topPosts = getHighPerformingPosts();
  if (topPosts.length === 0) return "";

  let context =
    "\n【過去に反応が良かった投稿例（これらを参考にしてください）】\n";
  topPosts.forEach((p, i) => {
    context += `例${i + 1}:\n${p.text}\n---\n`;
  });
  return context;
}

/**
 * 1セット（4件）の投稿を生成する
 */
function generatePostSet(keywordOrUrl, offset = 0) {
  const trendData = analyzeTrends();
  const trendContext = buildTrendContext(trendData);
  const posts = [];

  // 通常投稿を 3件まとめて生成（バッチ処理）
  Logger.log(
    `[PostGenerator] 通常投稿 ${POST_CONFIG.NORMAL_POSTS_PER_SET}件のバッチ生成を開始...`,
  );
  let batchTexts = generateNormalPostsBatch(
    trendData,
    offset,
    POST_CONFIG.NORMAL_POSTS_PER_SET,
  );

  for (let i = 0; i < POST_CONFIG.NORMAL_POSTS_PER_SET; i++) {
    posts.push({
      type: "normal",
      text: batchTexts[i] || `（通常投稿 ${i + 1} の生成に失敗しました）`,
      isThreadStart: i === 0,
    });
  }
  // API レート制限対策として待機 (バッチ処理によりリクエスト数は減ったものの念のため確保)
  Utilities.sleep(5000);

  // アフィリエイト投稿を 1件生成
  Logger.log("[PostGenerator] アフィリエイト投稿スロットの生成...");
  let affSuccess = false;
  let product = null;

  // 商品取得のリトライ（キーワードを変えて最大3回試行）
  for (let searchRetry = 0; searchRetry < 3; searchRetry++) {
    try {
      let currentKeyword = keywordOrUrl;
      if (searchRetry > 0 && keywordOrUrl.indexOf("http") !== 0) {
        // 2回目以降は違うキーワード（トレンドからランダム）を試す
        currentKeyword =
          trendData.keywords[
            Math.floor(Math.random() * trendData.keywords.length)
          ] || "人気";
      }

      product =
        currentKeyword.indexOf("http") === 0
          ? getRakutenProductByUrl(currentKeyword)
          : searchRakutenProduct(currentKeyword, trendData);

      if (product) break;
      Logger.log(`[PostGenerator] 商品取得リトライ ${searchRetry + 1}/3...`);
      Utilities.sleep(1000);
    } catch (e) {
      Logger.log(`[PostGenerator] 商品取得エラー: ${e.message}`);
    }
  }

  if (product) {
    let affPostText = "";
    let retries = 0;
    while (!affPostText && retries < 5) {
      // リトライ回数を5回に増加
      try {
        affPostText = generateAffiliatePost(product, trendContext);
      } catch (genErr) {
        Logger.log(
          `[PostGenerator] アフィリエイト生成エラー: ${genErr.message}`,
        );
      }
      if (!affPostText) {
        Logger.log(
          `[PostGenerator] アフィリエイト投稿リトライ ${retries + 1}/5`,
        );
        Utilities.sleep(2000);
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
      affSuccess = true;
    }
  } else {
    Logger.log(
      "[PostGenerator] !! 複数回試行しましたがアフィリエイト商品の取得に失敗しました。",
    );
  }

  // アフィリエイトが失敗した場合、通常投稿で確実に4件目を埋める
  if (!affSuccess) {
    Logger.log(
      "[PostGenerator] !! アフィリエイト生成が要件を満たさなかったため、通常投稿でフォールバックします。",
    );
    let fallbackText = "";
    try {
      let retries = 0;
      while (!fallbackText && retries < 3) {
        try {
          // フォールバック用に1件だけ生成
          const fbTexts = generateNormalPostsBatch(trendData, offset + 3, 1);
          fallbackText = fbTexts[0] || "";
        } catch (fbErr) {
          Logger.log(
            `[PostGenerator] フォールバック生成エラー: ${fbErr.message}`,
          );
        }
        if (!fallbackText) {
          Logger.log(
            `[PostGenerator] フォールバック通常投稿リトライ ${retries + 1}/3`,
          );
          Utilities.sleep(2000);
        }
        retries++;
      }
    } catch (e) {
      Logger.log(
        `[PostGenerator] フォールバック処理中にエラーが発生しました: ${e.message}`,
      );
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
 * 通常投稿を複数件まとめてバッチ生成する
 * 1回のリクエストで複数件分のテキストを配列で返す
 */
function generateNormalPostsBatch(trendData, offset, count) {
  const defaultStyles = [
    "共感・あるある（読者が「わかる」と頷く内容）",
    "有益な知恵袋（意外と知らないライフハック）",
    "失敗からの学び（親近感と教訓）",
    "時短・効率化テクニック（即実行できるコツ）",
    "マインドセット（前向きになれる考え方）",
    "ガジェット/アプリ紹介（使いこなし術）",
    "質問・アンケート型（リプライを促す構成）",
    "名言と一言（心に響く言葉と短い添え文）",
    "ユーモア（くすっと笑える日常のネタ）",
    "グルメ・レシピ（簡単・時短でおいしい食の話題）",
    "旅行・観光スポット（いつか行きたい素敵な場所）",
    "前向きメッセージ（明日が楽しみになる言葉）",
    "プチ贅沢（自分へのご褒美や小さな幸せ）",
    "癒しのひととき（リラックスできる習慣やアイテム）",
  ];
  const configStyles = POST_CONFIG.NORMAL_POST_STYLES;
  const styles = configStyles.length > 0 ? configStyles : defaultStyles;

  const focusKeyword =
    trendData.keywords[Math.floor(Math.random() * trendData.keywords.length)] ||
    "生産性";
  const month = new Date().getMonth() + 1;
  const successfulPostsContext = buildSuccessfulPostsContext();

  const platformName =
    POST_CONFIG.PLATFORM === "twitter" ? "X（Twitter）" : "Threads";

  // X（Twitter）専用の構成ヒント
  const xStructureHints =
    POST_CONFIG.PLATFORM === "twitter"
      ? `
【X（Twitter）専用 構成ルール】
・1行目に「結論」または「共感を呼ぶ一言」を置いてください。タイムラインで目を止めてもらえるかが勝負です。
・改行を効果的に使い、スマホ画面で読みやすいレイアウトにしてください。
・箇条書き（・や→）を活用し、情報密度と視認性を両立させてください。
・語尾を体言止めや「〜だよね」等の口語にして、Xらしいテンポ感を出してください。
・全角${POST_CONFIG.NORMAL_POST_MAX_CHARS}文字は非常に少ないため、無駄な修飾語や接続詞を徹底的にカットしてください。
`
      : "";

  let instructions = "";
  for (let i = 0; i < count; i++) {
    const style = styles[(offset + i) % styles.length];
    instructions += `\n【投稿${i + 1}の指示】\n・テーマ: 「${focusKeyword}」を自然な形で組み込むこと\n・スタイル: 「${style}」\n`;
  }

  const prompt = `あなたは${platformName}で「${TREND_CONFIG.TARGET_DEMO}」層から絶大な支持を得ているインフルエンサーです。

【重要制約】
・「テーマ：」や「生産性：」などのタイトル・見出しは一切不要です。冒頭から本文を開始してください。
・「はい」「承知しました」などの会話文や前置きは厳禁です。
・現在は${month}月です。必ずこの時期に相応しい内容にしてください。
・投稿本文のみを出力してください。
・「～ですか？」や「どう思いますか？」などの、読者への問いかけや意見を求める表現は一切禁止です。
・一人称（自分自身の呼び方）は必ず「僕」で統一してください。
${xStructureHints}
【★文字数制限【厳守】★】
・各投稿はそれぞれ必ず全角${POST_CONFIG.NORMAL_POST_MAX_CHARS}文字以内に収めてください。
・短くインパクトのある文章を心がけてください。

【今回の指示】
以下の条件に従い、${count}件の投稿テキストを生成してください。
ハッシュタグは各投稿1個のみ。絵文字は控えめに（各1つまで）。
読者に寄り添う「等身大」のトーンで、${platformName}らしいテンポ感のある文章を生成してください。

【出力形式（厳守）】
以下の区切り文字「===POST===」で各投稿を厳密に区切って出力してください。他の説明文は不要です。
（例）
投稿1の出力テキスト
===POST===
投稿2の出力テキスト
===POST===
...

${instructions}
${successfulPostsContext}
`;

  let batchResult = [];
  let retries = 0;

  while (batchResult.length < count && retries < 3) {
    try {
      const rawText = callGeminiAPI(prompt);
      const rawPosts = rawText
        .split("===POST===")
        .map((t) => t.trim())
        .filter((t) => t.length > 0);

      batchResult = [];
      for (let i = 0; i < count; i++) {
        if (rawPosts[i]) {
          let text = cleanPostText(rawPosts[i]);
          const max = POST_CONFIG.NORMAL_POST_MAX_CHARS;
          if (text.length > max) {
            Logger.log(
              `[PostGenerator] バッチ: 通常投稿 ${i + 1} が制限を超過(${text.length}/${max})。切り詰めます。`,
            );
            text = text.substring(0, max - 3) + "...";
          }
          batchResult.push(text);
        } else {
          batchResult.push(""); // 失敗時は空文字
        }
      }

      const successCount = batchResult.filter((t) => t.length > 0).length;
      if (successCount >= count) {
        break; // すべて成功
      } else {
        Logger.log(
          `[PostGenerator] バッチ生成 ${successCount}/${count} 成功、欠損があるためリトライします。`,
        );
        Utilities.sleep(2000);
      }
    } catch (e) {
      Logger.log(`[PostGenerator] バッチ生成エラー: ${e.message}`);
      Utilities.sleep(2000);
    }
    retries++;
  }

  // 足りない場合は空文字でパディング
  while (batchResult.length < count) {
    batchResult.push("");
  }

  return batchResult;
}

/**
 * アフィリエイト投稿を生成
 */
function generateAffiliatePost(product, trendContext) {
  const month = new Date().getMonth() + 1;
  const successfulPostsContext = buildSuccessfulPostsContext();
  const platformName =
    POST_CONFIG.PLATFORM === "twitter" ? "X（Twitter）" : "Threads";
  // Xの場合はURLは23文字固定、Threadsの場合は実数
  const urlCharCount =
    POST_CONFIG.PLATFORM === "twitter" ? 23 : product.url.length;
  const metaOverhead = urlCharCount + 2; // 改行等のバッファ（#PR削除）
  const bodyCharTarget =
    POST_CONFIG.AFFILIATE_POST_MAX_CHARS - metaOverhead - 10;

  // X（Twitter）専用のアフィリエイト構成ヒント（Threadsの場合は空文字）
  const xAffHints =
    POST_CONFIG.PLATFORM === "twitter"
      ? `
【X（Twitter）専用 構成ルール】
・1行目に「おっ」と思わせるフック（体験談・数字・意外性）を入れてください。
・商品の魅力を1〜2点に絞り、箇条書きではなく短い文で伝えてください。
・URLの前に改行を入れ、タップしやすくしてください。
・本文は全角${bodyCharTarget}文字以内に収めてください（URLはシステムが自動付与します）。
・語尾は口語（〜だよ / 〜してみて）で統一してください。
`
      : "";

  const prompt = `あなたは${platformName}で「${TREND_CONFIG.TARGET_DEMO}」層に向けて、本当に良いモノだけを勧めるキュレーターです。

【紹介商品詳細】
・名称: ${product.name}
・価格: ${product.price}円
・レビュー: 平均${product.reviewAvg}点 (${product.reviewCount}件)
・キャプション（参考）: ${product.caption ? product.caption.substring(0, 300) : "なし"}
・商品URL: ${product.url}

【文脈情報】
${trendContext}
${xAffHints}
【★文字数制限【厳守】★】
・URLとタグを含めた最終的な投稿を、全角${POST_CONFIG.AFFILIATE_POST_MAX_CHARS}文字以内に収める必要があります。
・システムが後からURL等（約${metaOverhead}文字分）を付与するため、本文メッセージは全角${bodyCharTarget}文字程度を目安に作成してください。

【構成指示】
・${product.name}の具体的な魅力や使い心地を記述 ＋ ${product.url} ＋ 関連ハッシュタグ（1個のみ）
・現在は${month}月です。今の時期にこの商品が必要な理由を${month}月の季節感と絡めてください。
・「PRであること」を隠さず、かつ自然なトーンでURLへの誘導を行ってください。
・投稿本文のみをそのまま出力してください。
・一人称は必ず「僕」で統一してください。
${successfulPostsContext}
`;

  let bodyText = "";
  for (let r = 0; r < 3; r++) {
    // 内部リトライも3回に増加
    bodyText = cleanPostText(callGeminiAPI(prompt));
    // 140文字制限(X)の場合は短めでも受理、Threadsの場合は従来どおり
    const minLen =
      POST_CONFIG.PLATFORM === "twitter"
        ? 30
        : POST_CONFIG.AFFILIATE_POST_MIN_CHARS - 30;
    if (bodyText.length >= minLen) break;
    Utilities.sleep(1000);
  }

  // 最終的な組み立て
  let finalText = bodyText;
  if (finalText.indexOf(product.url) === -1) finalText += "\n" + product.url;

  // 最終文字数チェック
  const max = POST_CONFIG.AFFILIATE_POST_MAX_CHARS;
  // 実際に見える文字数（XのURL短縮を考慮）で判定
  const visibleLen = finalText.length - product.url.length + urlCharCount;

  if (visibleLen > max) {
    Logger.log(
      `[PostGenerator] アフィリエイト投稿が制限を超過(${visibleLen}/${max})。切り詰めます。`,
    );
    const metaText = `\n${product.url}`;
    // 本文として許容できる長さを再計算
    const allowedBodyLen = max - metaOverhead - 3;
    finalText = bodyText.substring(0, allowedBodyLen) + "..." + metaText;
  }

  return finalText;
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

  // プレースホルダ検知（[ ] や 〇〇 など。ただし、URLなどは除外）
  const placeholderPattern = /\[[^h][^t][^t].*?\]|〇{2,}|○{2,}|◯{2,}|△{2,}/;
  if (
    placeholderPattern.test(cleaned) ||
    cleaned.includes("ブランド名") ||
    (cleaned.includes("〇〇") && !cleaned.includes("http"))
  ) {
    Logger.log(
      "[PostGenerator] プレースホルダを検出したため破棄: " +
        cleaned.substring(0, 20),
    );
    return "";
  }

  // 日本語が1文字でも含まれていれば OK とする（より柔軟に）
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
