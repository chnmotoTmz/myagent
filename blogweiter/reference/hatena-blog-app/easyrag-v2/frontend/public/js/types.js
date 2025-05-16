/**
 * @typedef {Object} Message
 * @property {string} id - メッセージID
 * @property {string} type - メッセージタイプ
 * @property {string} timestamp - タイムスタンプ
 * @property {string} content - メッセージ内容
 * @property {string} [file_path] - ファイルパス（オプショナル）
 */

/**
 * @typedef {Object} GeneratedContent
 * @property {string} content - 生成された記事の内容
 * @property {string} [summary] - 要約（オプショナル）
 */

/**
 * @typedef {Object} SearchResult
 * @property {string} id - 記事のID
 * @property {string} title - 記事のタイトル
 * @property {string} text_content - 記事の本文
 * @property {number} similarity_score - 類似度スコア
 */

/**
 * @typedef {Object} ApiResponse
 * @property {SearchResult[]} results - 検索結果の配列
 * @property {string} content - 生成された記事の内容
 */

/**
 * @typedef {Object} SearchRequest
 * @property {string} instruction - 指示内容
 * @property {string} query - 検索クエリ
 * @property {number} top_n - 取得する結果の数
 */ 