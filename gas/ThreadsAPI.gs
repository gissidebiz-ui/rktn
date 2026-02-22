/**
 * ============================================================
 * ThreadsAPI.gs — Threads API 通信モジュール
 * ============================================================
 * Threads Graph API を使用して、テキスト投稿やスレッド（リプライ）
 * を構築・公開します。
 * ============================================================
 */

/**
 * 投稿コンテナを作成する
 */
function createThreadsContainer(text, replyToId) {
  const url = `${THREADS_API_CONFIG.BASE_URL}/${CONFIG.THREADS_USER_ID}/threads`;
  const payload = {
    media_type: "TEXT",
    text: text,
    access_token: CONFIG.THREADS_ACCESS_TOKEN,
  };
  if (replyToId) payload.reply_to_id = replyToId;

  if (DRY_RUN) {
    Logger.log(`[ThreadsAPI][DRY] コンテナ作成: ${text.substring(0, 30)}...`);
    return "dry_run_container_" + Date.now();
  }

  const response = UrlFetchApp.fetch(url, {
    method: "post",
    payload: payload,
    muteHttpExceptions: true,
  });
  const res = JSON.parse(response.getContentText());
  if (!res.id) throw new Error(`コンテナ失敗: ${JSON.stringify(res)}`);
  return res.id;
}

/**
 * コンテナを公開する
 */
function publishThreadsContainer(creationId) {
  const url = `${THREADS_API_CONFIG.BASE_URL}/${CONFIG.THREADS_USER_ID}/threads_publish`;
  const payload = {
    creation_id: creationId,
    access_token: CONFIG.THREADS_ACCESS_TOKEN,
  };

  if (DRY_RUN) return "dry_run_post_" + Date.now();

  const response = UrlFetchApp.fetch(url, {
    method: "post",
    payload: payload,
    muteHttpExceptions: true,
  });
  const res = JSON.parse(response.getContentText());
  if (!res.id) throw new Error(`公開失敗: ${JSON.stringify(res)}`);
  return res.id;
}

/**
 * 単発投稿
 */
function publishTextPost(text) {
  const containerId = createThreadsContainer(text);
  Utilities.sleep(THREADS_API_CONFIG.PUBLISH_WAIT_MS);
  return publishThreadsContainer(containerId);
}

/**
 * リプライ投稿
 */
function publishReply(parentId, text) {
  const containerId = createThreadsContainer(text, parentId);
  Utilities.sleep(THREADS_API_CONFIG.PUBLISH_WAIT_MS);
  return publishThreadsContainer(containerId);
}

/**
 * 4件セットをスレッドとして一括投稿
 */
function publishPostSetAsThread(postSet) {
  Logger.log(`[ThreadsAPI] スレッド投稿開始 (${postSet.length}件)`);
  const results = [];
  let parentId = null;

  for (let i = 0; i < postSet.length; i++) {
    const post = postSet[i];
    try {
      let postId;
      if (i === 0) {
        postId = publishTextPost(post.text);
        parentId = postId;
      } else {
        Utilities.sleep(THREADS_API_CONFIG.REPLY_DELAY_MS);
        postId = publishReply(parentId, post.text);
      }
      results.push({
        row: post.row,
        success: true,
        postId: postId,
        parentId: i > 0 ? parentId : "",
      });
      Logger.log(`[ThreadsAPI] 成功 ${i + 1}/${postSet.length}: ${postId}`);
    } catch (e) {
      Logger.log(`[ThreadsAPI] 失敗 ${i + 1}/${postSet.length}: ${e.message}`);
      results.push({ row: post.row, success: false, error: e.message });
    }
  }
  return results;
}
