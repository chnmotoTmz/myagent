# Redmine連携テスト手順

このドキュメントでは、Gemini Blog ProcessorとRedmineチケット管理エージェント間の連携をテストする手順を説明します。

## 前提条件

1. Gemini Blog Processorが起動している
2. Redmineチケット管理エージェントが起動しており、APIが利用可能
3. 設定ファイル(.env)にRedmine連携のための設定が正しく設定されている

## テスト手順

### 1. テキストメッセージのRedmine転送テスト

```bash
curl -X POST http://localhost:8001/api/receive_message \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "test_message_1",
    "user_id": "test_user_123",
    "message_type": "text",
    "content": "これはRedmine連携のテスト用メッセージです。"
  }'
```

#### 期待される結果
- ステータスコード: 202 (Accepted)
- Gemini Blog ProcessorのログにRedmine連携の成功メッセージが表示される
- Redmineチケット管理エージェント側でメッセージが受信される

### 2. Redmineコマンドの処理テスト

```bash
curl -X POST http://localhost:8001/api/receive_message \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "test_command_1",
    "user_id": "test_user_123",
    "message_type": "text",
    "content": "@help"
  }'
```

#### 期待される結果
- ステータスコード: 202 (Accepted)
- RedmineからヘルプメッセージのレスポンスがGemini Blog Processorに返される
- 記事生成処理は実行されない

### 3. ブログ意図分析の転送テスト

```bash
# まず、ブログ種を生成
curl -X POST http://localhost:8001/api/webhook/trigger_process

# 次に、生成された意図分析をRedmineに転送（hour_keyは実際の値に置き換える）
curl -X POST http://localhost:8001/api/webhook/blog_intent/forward_to_redmine/202505160800 \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123"
  }'
```

#### 期待される結果
- ステータスコード: 200 (OK)
- Redmineチケット管理エージェント側で意図分析データを含むメッセージが受信される

### 4. 統合テスト（メッセージ受信からRedmine転送まで）

1. LINEウェブフックシミュレータでメッセージを送信
2. Gemini Blog Processorでメッセージが受信され、Redmineに転送される
3. ブログ種が生成される
4. 意図分析が実行される
5. 結果が自動的にRedmineに転送される

## エラーケースのテスト

### 1. Redmine連携が無効の場合

1. `.env`ファイルの`REDMINE_INTEGRATION_ENABLED`を`False`に設定
2. Gemini Blog Processorを再起動
3. テキストメッセージを送信して転送されないことを確認

### 2. Redmineサーバーが利用不可の場合

1. `.env`ファイルの`REDMINE_API_URL`を無効なURLに変更
2. Gemini Blog Processorを再起動
3. テキストメッセージを送信してエラーハンドリングが機能することを確認
4. エラーログが適切に記録されていることを確認

## トラブルシューティング

### 連携エラーが発生した場合

1. ログファイルを確認して具体的なエラーメッセージを特定
2. `.env`ファイルの設定が正しいことを確認
3. ネットワーク接続やファイアウォール設定を確認
4. `RedmineIntegrationService`のデバッグログ出力を有効にして詳細情報を取得

### Redmineからレスポンスがない場合

1. Redmineチケット管理エージェントのログを確認
2. APIエンドポイントの設定が正しいことを確認
3. APIキーが有効であることを確認
4. タイムアウト設定を調整してみる
