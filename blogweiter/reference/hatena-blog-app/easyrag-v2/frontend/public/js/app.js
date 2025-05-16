function messageApp() {
  const API_BASE_URL = 'http://localhost:8000';
  const API_CONFIG = {
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    }
  };

  return {
    messages: [],
    selectedId: null,
    selectedMessage: null,
    selectedGroup: [],
    loading: false,
    error: null,
    isGenerating: false,
    currentStep: 0,
    seedContent: null,
    ragCount: 5,
    ragResults: [],
    selectedRagResults: [],
    articleTitle: '',
    articleContent: null,
    articleTags: '',

    async init() {
      await this.refreshMessages();
    },

    async refreshMessages() {
      console.log('=== メッセージ更新開始 ===');
      this.loading = true;
      this.error = null;
      try {
        const response = await fetch(`${API_BASE_URL}/files`, {
          headers: API_CONFIG.headers
        });
        
        console.log('Response status:', response.status);
        const files = await response.json();
        console.log('Files response:', files);
        
        // ファイルが空の場合の処理
        if (!files || files.length === 0) {
          console.log('No files found');
          this.messages = [];
          return;
        }
        
        // メッセージをグループ化して取得
        const messageGroups = new Map();
        
        await Promise.all(
          files
            .filter(file => {
              const isValid = file.path.startsWith('line_messages/');
              console.log(`File ${file.path}: ${isValid ? '有効' : '無効'}`);
              return isValid;
            })
            .map(async file => {
              console.log(`Fetching file: ${file.path}`);
              const msgResponse = await fetch(`${API_BASE_URL}/file/${file.path}`, {
                headers: API_CONFIG.headers
              });
              
              if (!msgResponse.ok) {
                console.error(`Failed to fetch ${file.path}: ${msgResponse.status}`);
                return;
              }
              
              const messages = await msgResponse.json();
              console.log(`Messages from ${file.path}:`, messages);
              
              // メッセージの前処理
              messages.forEach(msg => {
                if (msg.type === 'image') {
                  msg.content = msg.content.replace('.jpg', '');
                }
              });

              // 同じタイムスタンプのメッセージをグループ化
              const baseTimestamp = messages[0]?.timestamp.split('.')[0];
              if (baseTimestamp) {
                if (!messageGroups.has(baseTimestamp)) {
                  messageGroups.set(baseTimestamp, []);
                }
                messageGroups.get(baseTimestamp).push(...messages);
              }
            })
        );

        // グループ化したメッセージを配列に変換
        this.messages = Array.from(messageGroups.entries()).map(([timestamp, group]) => ({
          id: timestamp,
          timestamp: timestamp,
          content: this.summarizeGroup(group),
          group: group
        }));

        console.log('Final messages:', this.messages);
        console.log('=== メッセージ更新完了 ===');

      } catch (error) {
        console.error('Error in refreshMessages:', error);
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },

    summarizeGroup(group) {
      const types = new Set(group.map(msg => msg.type));
      const summary = [];
      if (types.has('text')) summary.push('テキスト');
      if (types.has('image')) summary.push(`画像${group.filter(msg => msg.type === 'image').length}枚`);
      return summary.join(', ');
    },

    selectMessage(id) {
      this.selectedId = id;
      const message = this.messages.find(msg => msg.id === id);
      if (message) {
        this.selectedMessage = message;
        this.selectedGroup = message.group;
      } else {
        this.error = 'メッセージが見つかりません';
        this.selectedGroup = [];
      }
    },

    // 記事生成プロセスのメソッド
    startGeneration() {
      this.isGenerating = true;
      this.currentStep = 1;
      this.resetGenerationState();
    },

    closeGeneration() {
      this.isGenerating = false;
      this.resetGenerationState();
    },

    resetGenerationState() {
      this.currentStep = 1;
      this.seedContent = null;
      this.ragResults = [];
      this.selectedRagResults = [];
      this.articleTitle = '';
      this.articleContent = null;
      this.articleTags = '';
      this.error = null;
    },

    // Step 1: 種記事生成
    async generateSeed() {
      try {
        const response = await fetch(`${API_BASE_URL}/generate`, {  // ← URLを修正
          method: 'POST',
          headers: API_CONFIG.headers,
          body: JSON.stringify({ messages: this.selectedGroup })
        });

        if (!response.ok) throw new Error('種記事の生成に失敗しました');
        const data = await response.json();
        this.seedContent = data.content;
      } catch (error) {
        this.error = error.message;
      }
    },

    confirmSeed() {
      if (!this.seedContent) {
        this.error = '種記事を生成してください';
        return;
      }
      this.currentStep = 2;
    },

    // Step 2: RAG検索
    async searchRag() {
      console.log('searchRag called');
      try {
        if (!this.seedContent) {
          this.error = '種記事が必要です';
          return;
        }

        this.loading = true;
        this.error = null;
        this.ragResults = [];

        const response = await fetch(`${API_BASE_URL}/api/analyze`, {  // ← URLを修正
          method: 'POST',
          headers: API_CONFIG.headers,
          body: JSON.stringify({
            query: this.seedContent,
            top_n: parseInt(this.ragCount) || 5
          })
        });

        if (!response.ok) {
          const errorText = await response.text();
          console.error('Error response:', errorText);
          throw new Error('RAG検索に失敗しました');
        }

        const data = await response.json();
        console.log('Search results:', data);

        if (!data.results || !Array.isArray(data.results)) {
          throw new Error('不正な検索結果フォーマット');
        }

        this.ragResults = data.results.map(result => ({
          title: result.title || '関連記事',
          text_content: result.text_content || '',
          similarity_score: result.similarity_score || 0
        }));

        if (this.ragResults.length === 0) {
          this.error = '類似記事が見つかりませんでした';
        }

      } catch (error) {
        console.error('RAG search error:', error);
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },

    toggleRagResult(index) {
      const position = this.selectedRagResults.indexOf(index);
      if (position === -1) {
        this.selectedRagResults.push(index);
      } else {
        this.selectedRagResults.splice(position, 1);
      }
    },

    confirmRag() {
      if (this.selectedRagResults.length === 0) {
        this.error = '類似記事を選択してください';
        return;
      }
      this.currentStep = 3;
    },

    // Step 3: 記事生成
    async generateArticle() {
      try {
        if (!this.seedContent) {
          throw new Error('種記事が必要です');
        }

        const response = await fetch(`${API_BASE_URL}/api/generate-full`, {
          method: 'POST',
          headers: API_CONFIG.headers,
          body: JSON.stringify({
            seed: this.seedContent,
            references: this.selectedRagResults.map(i => this.ragResults[i])
          })
        });

        if (!response.ok) {
          throw new Error('記事生成に失敗しました');
        }

        const data = await response.json();
        this.articleTitle = data.title;
        this.articleContent = data.content;
        this.articleTags = data.tags.join(', ');
      } catch (error) {
        this.error = error.message;
      }
    },

    confirmArticle() {
      if (!this.articleTitle || !this.articleContent) {
        this.error = '記事を生成してください';
        return;
      }
      this.currentStep = 4;
    },

    // Step 4: はてなブログ投稿
    async postToHatena() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/post-hatena`, {  // ← URLを修正
          method: 'POST',
          headers: API_CONFIG.headers,
          body: JSON.stringify({
            title: this.articleTitle,
            content: this.articleContent,
            tags: this.articleTags.split(',').map(tag => tag.trim())
          })
        });

        if (!response.ok) throw new Error('はてなブログへの投稿に失敗しました');
        const data = await response.json();
        alert(`投稿が完了しました: ${data.url}`);
        this.closeGeneration();
      } catch (error) {
        this.error = error.message;
      }
    },

    formatDate(timestamp) {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      return `${date.getFullYear()}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    }
  }
}

document.addEventListener('alpine:init', () => {
    Alpine.data('searchApp', () => ({
        instruction: '',
        query: '',
        results: [],
        generatedContent: '',
        isLoading: false,
        error: null,

        async search() {
            if (!this.query.trim()) {
                this.error = '検索クエリを入力してください';
                return;
            }

            this.isLoading = true;
            this.error = null;

            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        instruction: this.instruction,
                        query: this.query,
                        top_n: 5
                    }),
                });

                if (!response.ok) {
                    throw new Error('検索中にエラーが発生しました');
                }

                const data = await response.json();
                this.results = data.results;
                this.generatedContent = data.content;

            } catch (error) {
                console.error('Error:', error);
                this.error = error.message;
            } finally {
                this.isLoading = false;
            }
        },

        marked(content) {
            return marked.parse(content);
        }
    }));
}); 