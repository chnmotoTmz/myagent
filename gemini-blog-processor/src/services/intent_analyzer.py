"""
ブログ記事の意図を分析するサービス
"""
import json
import logging
from typing import Dict, Optional, Any, Tuple

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from src.database import db
from src.models.blog_seed import BlogSeed
from src.models.blog_intent import BlogIntentAnalysis
from src.config import GEMINI_API_KEY, GEMINI_TIMEOUT

# ロギング設定
logger = logging.getLogger(__name__)

class IntentAnalysisManager:
    """ブログ記事の意図を分析し、結果を管理するクラス"""
    
    def __init__(self):
        self._setup_gemini()
    
    def _setup_gemini(self) -> None:
        """Gemini APIのセットアップ (提供された設定を反映)"""
        if not GEMINI_API_KEY:
            logger.error("Gemini API key not configured in environment variables")
            return

        try:
            genai.configure(api_key=GEMINI_API_KEY)
            
            # 意図分析用モデル (Gemini 2.5 Flash Preview)
            # 提供された設定を反映
            self.model = genai.GenerativeModel(
                "gemini-2.5-flash-preview-04-17",
                generation_config={
                    "temperature": 1.0,  # 高温設定でクリエイティブな出力
                    "candidate_count": 1
                }
            )
            logger.info("Gemini API configured for intent analysis with web search")
        except Exception as e:
            logger.error(f"Gemini setup failed: {e}")
            self.model = None
    
    def analyze_intent(self, hour_key: str) -> Optional[BlogIntentAnalysis]:
        """ブログ記事の意図を分析する
        
        Args:
            hour_key: 分析対象の記事のhour_key
            
        Returns:
            分析結果のBlogIntentAnalysisオブジェクト、エラー時はNone
        """
        # self.current_hour_key = hour_key # Store hour_key for logging in _generate_intent_analysis <- 削除
        # BlogSeedを取得
        blog_seed = db.session.get(BlogSeed, hour_key)
        if not blog_seed:
            logger.error(f"Blog seed not found for hour_key: {hour_key}")
            return None

        # 既存の分析があるか確認
        existing_analysis = BlogIntentAnalysis.query.filter_by(hour_key=hour_key).first()
        if existing_analysis:
            logger.info(f"Intent analysis already exists for hour_key: {hour_key}")
            return existing_analysis
        
        # Gemini APIで意図を分析
        analysis_result, raw_response = self._generate_intent_analysis(
            blog_seed.markdown_content,
            hour_key # hour_keyを引数として渡す
        )
        if not analysis_result:
            logger.error(f"Failed to analyze intent for hour_key: {hour_key}")
            return None
        
        try:
            # 分析結果をパース
            intent_analysis = BlogIntentAnalysis(
                hour_key=hour_key,
                intent_category=analysis_result.get("intent_category", "未分類"),
                intent_description=analysis_result.get("intent_description", "分析不能"),
                confidence_score=float(analysis_result.get("confidence_score", 0.0)),
                target_audience=analysis_result.get("target_audience", ""),
                emotional_tone=analysis_result.get("emotional_tone", ""),
                call_to_action=analysis_result.get("call_to_action", ""),
                raw_response=raw_response
            )
            
            # データベースに保存
            db.session.add(intent_analysis)
            db.session.commit()
            logger.info(f"Saved intent analysis for hour_key: {hour_key}")
            
            return intent_analysis
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving intent analysis: {e}")
            return None
    
    def _generate_intent_analysis(self, markdown_content: str, hour_key_for_logging: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Gemini APIを使用して投稿の意図を分析する
        
        Args:
            markdown_content: 分析対象のマークダウンコンテンツ
            hour_key_for_logging: ロギング用のhour_key (オプション)

        Returns:
            (分析結果のディクショナリ, APIからの生の応答テキスト)
        """
        if not self.model:
            logger.error("Gemini model not configured")
            return None, None

        log_hour_key = hour_key_for_logging if hour_key_for_logging else "N/A"
        try:
            # 投稿意図分析のためのプロンプト (Thinking mode対応)
            prompt = f"""
            # 分析対象コンテンツ
            ```markdown
            {markdown_content}
            ```

            # 分析指示
            上記のマークダウン形式のコンテンツを詳しく分析し、以下の点について考えてください。

            ## 考えるステップ:
            1. まず内容を十分に理解する
            2. どのような目的でこの投稿が書かれたのか考える
            3. 対象読者は誰か検討する
            4. 感情的な色調を確認する
            5. 行動喚起（Call to Action）の有無を確認する

            ## 回答形式:
            分析結果を以下のJSONフォーマットで提供してください。

            ```json
            {{
              "intent_category": "投稿の主な意図カテゴリ",
              "intent_description": "投稿の意図の詳細な説明（200文字以内）",
              "confidence_score": 0.0〜1.0の確信度,
              "target_audience": "想定されるターゲットオーディエンス",
              "emotional_tone": "投稿の感情的トーン",
              "call_to_action": "投稿から読み取れる行動喚起（なければ空白）"
            }}
            ```

            意図カテゴリは以下から最適なものを選んでください:
            - 情報共有: 事実や情報を単に共有するだけの投稿
            - 説得・啓発: 読者の考えや行動を変えようとする投稿
            - 比較分析: 複数のものを比較して違いを示す投稿
            - 感情表現: 感情や個人的な体験を表現する投稿
            - 問題提起: 問題点を指摘し議論を促す投稿
            - 宣伝・広告: 製品やサービスを宣伝する投稿
            - エンターテイメント: 楽しませることを目的とした投稿

            感情的トーンの例:
            - 中立: 事実重視で感情を抑えた表現
            - ポジティブ: 肯定的で前向きな表現
            - ネガティブ: 批判的や懸念を示す表現
            - 熱意的: 強い感情や情熱を示す表現
            - 説得的: 読者を説得しようとする表現
            - 教育的: 教えるような立場からの表現

            分析は深く、しかし結果はJSONフォーマットで明確に提供してください。
            """
            
            # Gemini APIコール
            response = self.model.generate_content(
                prompt,
                request_options={"timeout": GEMINI_TIMEOUT * 2}
            )
            
            if not hasattr(response, "text") or not response.text:
                logger.error("Empty response from Gemini API")
                return None, None
            
            raw_response = response.text
            logger.info(f"Raw response from Gemini for intent analysis (hour_key: {log_hour_key}):\n{raw_response}")
            
            # JSON部分を抽出
            json_text = raw_response
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()

            # JSONパース
            logger.info(f"Attempting to parse JSON for intent analysis (hour_key: {log_hour_key}):\n{json_text}")
            result = json.loads(json_text)
            logger.info(f"Successfully analyzed intent with category: {result.get('intent_category')}")
            return result, raw_response
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}, raw response: {response.text if hasattr(response, 'text') else 'None'}")
            return None, response.text if hasattr(response, "text") else None
        
        except google_exceptions.DeadlineExceeded:
            logger.error("Gemini API timeout exceeded")
            return None, None

        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return None, None
