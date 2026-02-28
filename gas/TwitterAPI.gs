/**
 * ============================================================
 * TwitterAPI.gs — X（Twitter）API 通信モジュール
 * ============================================================
 * OAuth 1.0a 署名を GAS 標準の Utilities.computeHmacSignature で構築し、
 * Twitter API v2 を使用してテキスト投稿を行います。
 *
 * 【必要なスクリプトプロパティ】
 *   - TWITTER_API_KEY
 *   - TWITTER_API_SECRET
 *   - TWITTER_ACCESS_TOKEN
 *   - TWITTER_ACCESS_SECRET
 * ============================================================
 */

// ============================================================
// RFC 3986 準拠のパーセントエンコード
// ============================================================
function percentEncode(str) {
  return encodeURIComponent(str)
    .replace(/!/g, "%21")
    .replace(/\*/g, "%2A")
    .replace(/'/g, "%27")
    .replace(/\(/g, "%28")
    .replace(/\)/g, "%29");
}

// ============================================================
// ランダムな nonce 文字列を生成
// ============================================================
function generateNonce() {
  const chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let result = "";
  for (let i = 0; i < 32; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

// ============================================================
// OAuth 1.0a 署名付き Authorization ヘッダーを構築
// ============================================================
function buildOAuthHeader(method, url, bodyParams) {
  const apiKey = CONFIG.TWITTER_API_KEY;
  const apiSecret = CONFIG.TWITTER_API_SECRET;
  const accessToken = CONFIG.TWITTER_ACCESS_TOKEN;
  const accessSecret = CONFIG.TWITTER_ACCESS_SECRET;

  if (!apiKey || !apiSecret || !accessToken || !accessSecret) {
    throw new Error(
      "[TwitterAPI] Twitter API の認証キーが設定されていません。スクリプトプロパティを確認してください。",
    );
  }

  // OAuth パラメータ
  const oauthParams = {
    oauth_consumer_key: apiKey,
    oauth_nonce: generateNonce(),
    oauth_signature_method: "HMAC-SHA1",
    oauth_timestamp: Math.floor(Date.now() / 1000).toString(),
    oauth_token: accessToken,
    oauth_version: "1.0",
  };

  // 署名ベース文字列の構築
  // Twitter API v2 では JSON body を署名に含めない（POST body が application/json の場合）
  // OAuth パラメータのみをソートして署名ベースに含める
  const allParams = Object.assign({}, oauthParams);

  // パラメータをキーでソートし、エンコードして結合
  const paramString = Object.keys(allParams)
    .sort()
    .map(function (key) {
      return percentEncode(key) + "=" + percentEncode(allParams[key]);
    })
    .join("&");

  const signatureBase =
    method.toUpperCase() +
    "&" +
    percentEncode(url) +
    "&" +
    percentEncode(paramString);

  // 署名キー
  const signingKey =
    percentEncode(apiSecret) + "&" + percentEncode(accessSecret);

  // HMAC-SHA1 署名を計算
  const signatureBytes = Utilities.computeHmacSignature(
    Utilities.MacAlgorithm.HMAC_SHA_1,
    signatureBase,
    signingKey,
  );
  const signature = Utilities.base64Encode(signatureBytes);

  oauthParams["oauth_signature"] = signature;

  // Authorization ヘッダーを組み立て
  const headerString = Object.keys(oauthParams)
    .sort()
    .map(function (key) {
      return percentEncode(key) + '="' + percentEncode(oauthParams[key]) + '"';
    })
    .join(", ");

  return "OAuth " + headerString;
}

// ============================================================
// X（Twitter）にテキスト投稿を行う
// ============================================================
/**
 * テキストを X に投稿する
 * @param {string} text - 投稿テキスト（全角140文字/半角280文字以内）
 * @param {string} parentId - 親ツイートのID（省略可）
 * @returns {string} ツイートID
 */
function postToTwitter(text, parentId) {
  const url = TWITTER_API_CONFIG.TWEET_ENDPOINT;

  if (DRY_RUN) {
    Logger.log(
      `[TwitterAPI][DRY] 投稿 (parent: ${parentId || "なし"}): ${text.substring(0, 50)}...`,
    );
    return "dry_run_tweet_" + Date.now();
  }

  const authHeader = buildOAuthHeader("POST", url, {});

  const payloadObj = { text: text };
  if (parentId) {
    payloadObj.reply = { in_reply_to_tweet_id: String(parentId) };
  }
  const payload = JSON.stringify(payloadObj);

  const options = {
    method: "post",
    contentType: "application/json",
    headers: {
      Authorization: authHeader,
    },
    payload: payload,
    muteHttpExceptions: true,
  };

  let response;
  let statusCode;
  let responseBody;
  let retryCount = 0;
  const maxRetries = 3;

  while (retryCount <= maxRetries) {
    try {
      response = UrlFetchApp.fetch(url, options);
      statusCode = response.getResponseCode();

      const contentText = response.getContentText();
      try {
        responseBody = JSON.parse(contentText);
      } catch (e) {
        responseBody = { detail: contentText || "JSONパースエラー" };
      }

      if (statusCode === 201 && responseBody.data && responseBody.data.id) {
        Logger.log(`[TwitterAPI] 投稿成功: ID=${responseBody.data.id}`);
        return responseBody.data.id;
      }

      // 500番台（Twitter側の一時的な障害）ならリトライ
      if (statusCode >= 500 && statusCode < 600 && retryCount < maxRetries) {
        retryCount++;
        const waitTime = retryCount * 3000; // 3秒, 6秒, 9秒待機
        Logger.log(
          `[TwitterAPI] 一時的なエラー(HTTP ${statusCode})。${waitTime}ms後に再試行します (${retryCount}/${maxRetries})`,
        );
        Utilities.sleep(waitTime);
        continue;
      }

      break; // 成功、またはリトライ対象外のエラーならループを抜ける
    } catch (e) {
      // ネットワーク切断などの例外
      if (retryCount < maxRetries) {
        retryCount++;
        Logger.log(
          `[TwitterAPI] 通信例外: ${e.message}。再試行します (${retryCount}/${maxRetries})`,
        );
        Utilities.sleep(retryCount * 3000);
        continue;
      }
      throw e;
    }
  }

  // エラーハンドリング
  const errorDetail =
    responseBody.detail || responseBody.title || JSON.stringify(responseBody);

  // レート制限チェック
  if (statusCode === 429) {
    Logger.log(
      `[TwitterAPI] レート制限に到達しました。待機後にリトライしてください。`,
    );
    throw new Error(`レート制限: ${errorDetail}`);
  }

  throw new Error(`[TwitterAPI] 投稿失敗 (HTTP ${statusCode}): ${errorDetail}`);
}

// ============================================================
// 複数の投稿を順番に単発投稿する（Threads のスレッド投稿の代替）
// ============================================================
/**
 * 投稿セットを順番に X へ投稿する
 * @param {Object[]} postSet - 投稿オブジェクトの配列 [{row, text, ...}]
 * @returns {Object[]} 結果配列 [{row, success, postId, error}]
 */
function publishPostSetToTwitter(postSet) {
  Logger.log(`[TwitterAPI] 一括投稿開始 (${postSet.length}件)`);
  const results = [];
  let lastTweetId = "";

  for (let i = 0; i < postSet.length; i++) {
    const post = postSet[i];
    try {
      let parentId = "";
      if (post.type === "affiliate_link" && lastTweetId) {
        parentId = lastTweetId;
      }

      const postId = postToTwitter(post.text, parentId);
      results.push({
        row: post.row,
        success: true,
        postId: postId,
        parentId: parentId,
      });
      Logger.log(`[TwitterAPI] 成功 ${i + 1}/${postSet.length}: ${postId}`);
      lastTweetId = postId;

      // レート制限対策: 投稿間に待機
      if (i < postSet.length - 1) {
        Utilities.sleep(TWITTER_API_CONFIG.POST_INTERVAL_MS);
      }
    } catch (e) {
      Logger.log(`[TwitterAPI] 失敗 ${i + 1}/${postSet.length}: ${e.message}`);
      results.push({ row: post.row, success: false, error: e.message });
      lastTweetId = ""; // ツリーをリセット
    }
  }
  return results;
}
