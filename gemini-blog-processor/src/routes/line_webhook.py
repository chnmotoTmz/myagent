"""
LINEメッセージを受信し、ブログ記事の種を生成するモジュール。

このモジュールは以下の機能を提供します：
1. LINEメッセージの受信と保存
2. Gemini AIによるブログ記事種の生成
3. 生成された記事種の管理
4. Redmineチケット管理エージェントとの連携
"""

from flask import Blueprint, request, jsonify
import os
import datetime
from datetime import timezone
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import logging
from sqlalchemy.exc import IntegrityError
from typing import Dict, Optional, Tuple, List

from src.database import db
from src.models import Message, BlogSeed
from src.services.redmine_integration import RedmineIntegrationService
import src.config as config

# ロギング設定
logger = logging.getLogger(__name__)
line_webhook_bp = Blueprint("line_webhook", __name__, url_prefix="/api/webhook")

# Gemini API設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_TIMEOUT = 60  # seconds

class WebhookHandler:
    """LINEメッセージの受信と基本的な処理を行うクラス"""
    
    @staticmethod
    def validate_message(data: Dict) -> Optional[str]:
        """受信したメッセージデータのバリデーション"""
        if not isinstance(data, dict):
            return "Invalid message format"

        required = ["user", "type", "message"]
        missing = [field for field in required if field not in data]
        if missing:
            return f"Missing fields: {', '.join(missing)}"
            
        return None

    @staticmethod
    def create_message(data: Dict) -> Message:
        """メッセージオブジェクトの作成"""
        message_id = data.get("messageId", WebhookHandler._generate_message_id())
        return Message(
            message_id=message_id,
            user_id=data["user"],
            message_type=data["type"],
            content=data["message"],
            timestamp=datetime.datetime.now(timezone.utc)
        )

    @staticmethod
    def _generate_message_id() -> str:
        """一意のメッセージIDを生成"""
        now = datetime.datetime.now(timezone.utc)
        return f"gen_{now.strftime('%Y%m%d%H%M%S%f')}"

class MessageProcessor:
    """メッセージの保存と管理を行うクラス"""

    @staticmethod
    def save_message(message: Message) -> Optional[str]:
        """
        メッセージをデータベースに保存
        
        Args:
            message: 保存するメッセージオブジェクト
            
        Returns:
            エラーメッセージ（エラーが発生した場合）
        """
        try:
            # 重複チェック
            if db.session.get(Message, message.message_id):
                return "Duplicate message"

            db.session.add(message)
            db.session.commit()
            logger.info(f"Message saved: {message.message_id}")
            return None

        except IntegrityError:
            db.session.rollback()
            logger.error(f"Database integrity error: {message.message_id}")
            return "Database integrity error"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save message: {e}")
            return f"Database error: {str(e)}"

    @staticmethod
    def get_messages_for_hour(hour_key: str) -> List[Message]:
        """指定された時間のメッセージを取得"""
        hour_start = datetime.datetime.strptime(hour_key, "%Y%m%d%H")
        hour_end = hour_start + datetime.timedelta(hours=1)

        return Message.query.filter(
            Message.timestamp >= hour_start,
            Message.timestamp < hour_end,
            Message.message_type == "text"
        ).order_by(Message.timestamp).all()

class ContentGenerator:
    """Gemini AIを使用してブログ記事の種を生成するクラス"""

    def __init__(self):
        self._setup_gemini()

    def _setup_gemini(self) -> None:
        """Gemini APIのセットアップ"""
        if not GEMINI_API_KEY:
            logger.error("Gemini API key not configured")
            return

        try:
            genai.configure(api_key=GEMINI_API_KEY)
            # テキスト生成用モデル
            self.text_model = genai.GenerativeModel("gemini-2.5-flash-preview-04-17")          # 画像処理用モデル
            self.vision_model = genai.GenerativeModel("gemini-2.5-flash-preview-04-17")
            logger.info("Gemini API configured")
        except Exception as e:
            logger.error(f"Gemini setup failed: {e}")
            self.text_model = None
            self.vision_model = None

    def generate_content(self, messages: List[Message]) -> Optional[str]:
        """メッセージリストからブログ記事の種を生成"""
        if not messages:
            return None

        if not hasattr(self, "text_model") or self.text_model is None:
            return "[Error: Gemini API not configured]"

        text = self._format_messages(messages)
        try:
            response = self.text_model.generate_content(
                self._create_prompt(text),
                request_options={"timeout": GEMINI_TIMEOUT}
            )
            return response.text if hasattr(response, "text") else None

        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return None

    def image_to_text(self, image_path: str) -> Optional[str]:
        """画像からその内容を説明するテキストを生成
        
        Args:
            image_path: 画像ファイルのパス
            
        Returns:
            画像の説明文。エラー時はNoneまたはエラーメッセージ
        """
        if not hasattr(self, "vision_model") or self.vision_model is None:
            logger.error("Gemini Vision model not configured")
            return "[Error: Gemini Vision API not configured]"
        
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return f"[Error: Image file not found: {image_path}]"
            
        try:
            logger.info(f"Processing image with Gemini Vision API: {image_path}")
            
            # 画像を読み込むためにPIL (Pillow)を使用
            try:
                from PIL import Image
                image = Image.open(image_path)
                logger.info(f"Successfully loaded image with PIL: {image.format}, size={image.size}")
                
                # 日本語で画像を説明するようにプロンプト設定
                prompt = """
                この画像に何が写っているか詳細に説明してください。
                できるだけ具体的に、以下の点に注目して分析してください：
                
                1. 主要な被写体
                2. 背景や環境
                3. 人物がいる場合はその様子
                4. 風景や物体の特徴
                5. 色彩や雰囲気
                
                日本語で回答してください。
                """
                
                # Gemini Vision APIを呼び出し - PILオブジェクトを直接渡す
                response = self.vision_model.generate_content(
                    [prompt, image],
                    request_options={"timeout": GEMINI_TIMEOUT * 2}
                )
                
                if hasattr(response, "text") and response.text:
                    logger.info(f"Successfully generated image description ({len(response.text)} chars)")
                    return response.text
                else:
                    logger.warning("Empty response from Gemini Vision API")
                    return "[画像からテキストを生成できませんでした]"
                    
            except ImportError:
                logger.error("PIL (Pillow) is not installed. Please install it using: pip install pillow")
                return "[エラー: PILライブラリがインストールされていません。'pip install pillow'を実行してください]"
                
        except google_exceptions.DeadlineExceeded:
            logger.error("Gemini API timeout exceeded")
            return "[エラー: API呼び出しがタイムアウトしました]"
        except Exception as e:
            logger.error(f"Image analysis failed: {str(e)}")
            return f"[画像分析中にエラーが発生しました: {str(e)}]"

    @staticmethod
    def _format_messages(messages: List[Message]) -> str:
        """メッセージをテキスト形式に整形"""
        return "\n\n".join([
            f'[{m.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}] '
            f'User {m.user_id}: {m.content}'
            for m in messages
        ])

    @staticmethod
    def _create_prompt(text: str) -> str:
        """ブログ記事生成用のプロンプトを作成"""
        return f"""以下のテキスト群を1時間単位で要約し、はてなブログの記事形式（Markdown）で種データを生成してください。

各時間のまとめは見出し（例：## HH:00 - HH:59）としてください。
重要な点を箇条書きで示し、関連する元のメッセージも引用してください。

--- TEXT START ---
{text}
--- TEXT END ---

はてなブログ記事:
"""

class BlogSeedManager:
    """生成されたブログ記事の種を管理するクラス"""

    @staticmethod
    def save_seed(hour_key: str, content: str) -> Optional[str]:
        """ブログ種をデータベースに保存（既存データがある場合は追加）"""
        try:
            seed = db.session.get(BlogSeed, hour_key)
            now = datetime.datetime.now(timezone.utc)
            
            if seed:
                # 既存の内容を維持しつつ、新しいコンテンツを追加
                # 現在時刻と一意識別子を含むセパレータを使用
                separator = f"\n\n## {now.strftime('%Y-%m-%d %H:%M:%S')} の追加コンテンツ\n\n"
                seed.markdown_content = seed.markdown_content + separator + content
                seed.updated_at = now
                logger.info(f"Appended content to existing blog seed: {hour_key}")
            else:
                # 新規作成
                seed = BlogSeed(
                    hour_key=hour_key,
                    markdown_content=content
                )
                db.session.add(seed)
                logger.info(f"Created new blog seed: {hour_key}")

            db.session.commit()
            logger.info(f"Blog seed saved: {hour_key}")
            return None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save blog seed: {e}")
            return str(e)

    @staticmethod
    def get_seed(hour_key: str) -> Optional[BlogSeed]:
        """指定された時間のブログ種を取得"""
        return db.session.get(BlogSeed, hour_key)

# --- Webhook Endpoints ---

@line_webhook_bp.route("/line", methods=["POST"])
def handle_line_webhook():
    """LINEメッセージを受信するエンドポイント"""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    try:
        data = request.get_json()
        logger.info("Received webhook data")
    except Exception as e:
        logger.error(f"JSON parse error: {e}")
        return jsonify({"error": "Invalid JSON"}), 400

    # メッセージの検証
    handler = WebhookHandler()
    if error := handler.validate_message(data):
        return jsonify({"error": error}), 400

    # メッセージの作成と保存
    message = handler.create_message(data)
    processor = MessageProcessor()
    if error := processor.save_message(message):
        if error == "Duplicate message":
            return jsonify({"info": "Duplicate message ignored"}), 200
        return jsonify({"error": error}), 500
      # Redmineチケット管理エージェントとの連携処理
    if config.REDMINE_INTEGRATION_ENABLED:
        try:
            # Redmine連携サービスのインスタンス化
            redmine_service = RedmineIntegrationService()
            
            message_text = message.content
            user_id = message.user_id
            reply_token = data.get("replyToken")  # LINEからのリプライトークン
            
            # コマンドメッセージかどうかの判定
            if redmine_service.is_command_message(message_text):
                if redmine_service.is_redmine_command(message_text):
                    # Redmineコマンドの処理
                    response = redmine_service.handle_redmine_command(
                        user_id=user_id,
                        message_text=message_text,
                        reply_token=reply_token
                    )
                    logger.info(f"Redmine command handled: {response.get('status', 'unknown')}")
                    
                elif not redmine_service.is_gemini_command(message_text):
                    # 不明なコマンドの場合はヘルプを表示するためRedmineに転送
                    redmine_service.forward_message(
                        user_id=user_id,
                        message_text="@help",  # ヘルプコマンドを送信
                        reply_token=reply_token
                    )
                    logger.info("Unknown command forwarded to Redmine as help request")
            else:
                # 通常メッセージの転送
                redmine_service.forward_message(
                    user_id=user_id,
                    message_text=message_text,
                    reply_token=reply_token
                )
                logger.info("Message forwarded to Redmine")
                
        except Exception as e:
            logger.error(f"Redmine integration error: {e}")
            # Redmine連携のエラーはアプリケーションの正常動作を阻害しないようにする

    return jsonify({
        "status": "success",
        "message": "Message received",
        "message_id": message.message_id    }), 200

@line_webhook_bp.route("/intent_process", methods=["POST"])
def forward_intent_to_redmine():
    """ブログ意図分析をRedmineチケット管理エージェントに転送するエンドポイント"""
    if not config.REDMINE_INTEGRATION_ENABLED:
        return jsonify({"error": "Redmine integration is disabled"}), 400
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
            
        hour_key = data.get("hour_key")
        user_id = data.get("user_id")
        
        if not hour_key or not user_id:
            return jsonify({"error": "hour_key and user_id are required"}), 400
            
        # BlogSeedとBlogIntentAnalysisの取得
        blog_seed = BlogSeedManager.get_seed(hour_key)
        if not blog_seed:
            return jsonify({"error": f"Blog seed not found for hour_key: {hour_key}"}), 404
            
        # BlogIntentAnalysisの取得
        from src.models.blog_intent import BlogIntentAnalysis
        intent_analysis = BlogIntentAnalysis.query.filter_by(hour_key=hour_key).first()
        if not intent_analysis:
            return jsonify({"error": f"Intent analysis not found for hour_key: {hour_key}"}), 404
            
        # Redmine連携サービスのインスタンス化
        redmine_service = RedmineIntegrationService()
        
        # 投稿意図データの作成
        intent_data = {
            "intent_category": intent_analysis.intent_category,
            "intent_description": intent_analysis.intent_description,
            "confidence_score": intent_analysis.confidence_score,
            "target_audience": intent_analysis.target_audience,
            "emotional_tone": intent_analysis.emotional_tone,
            "call_to_action": intent_analysis.call_to_action,
            "blog_content": blog_seed.markdown_content,
            "hour_key": hour_key
        }
        
        # Redmineチケット管理エージェントにデータを転送
        result = redmine_service.process_message_with_intent(
            user_id=user_id,
            message_text=f"ブログ記事の意図分析結果: {intent_analysis.intent_category}",
            intent_type=intent_analysis.intent_category,
            confidence_score=intent_analysis.confidence_score,
            keywords=[intent_analysis.target_audience, intent_analysis.emotional_tone] if intent_analysis.target_audience and intent_analysis.emotional_tone else []
        )
        
        return jsonify({
            "status": "success",
            "message": "Intent analysis forwarded to Redmine",
            "redmine_response": result
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to forward intent analysis to Redmine: {e}")
        return jsonify({"error": str(e)}), 500
        
@line_webhook_bp.route("/trigger_process", methods=["POST"])
def trigger_processing():
    """ブログ種生成処理を手動でトリガーするエンドポイント"""
    try:
        # 処理対象の時間を決定
        now = datetime.datetime.now(timezone.utc)
        hour_key = (now - datetime.timedelta(hours=1)).strftime("%Y%m%d%H")

        # メッセージの取得と処理
        messages = MessageProcessor.get_messages_for_hour(hour_key)
        if not messages:
            return jsonify({
                "status": "warning",
                "message": "No messages to process"
            }), 200

        # コンテンツの生成
        generator = ContentGenerator()
        content = generator.generate_content(messages)
        if not content:
            return jsonify({
                "status": "error",
                "message": "Content generation failed"
            }), 500        # ブログ種の保存
        manager = BlogSeedManager()
        if error := manager.save_seed(hour_key, content):
            return jsonify({"error": error}), 500        # Redmine連携が有効な場合、自動的に結果を転送
        if config.REDMINE_INTEGRATION_ENABLED:
            try:
                # BlogSeedの所有者を特定（この時間帯の最初のメッセージの送信者）
                first_message = messages[0] if messages else None
                if first_message:
                    user_id = first_message.user_id
                    
                    # 意図分析を実行
                    from src.services.intent_analyzer import IntentAnalysisManager
                    intent_manager = IntentAnalysisManager()
                    intent_analysis = intent_manager.analyze_intent(hour_key)
                    
                    if intent_analysis:
                        # Redmine連携サービスのインスタンス化
                        redmine_service = RedmineIntegrationService()
                        
                        # 意図分析結果をRedmineに転送
                        redmine_service.process_message_with_intent(
                            user_id=user_id,
                            message_text=f"[自動生成] ブログ記事の種: {hour_key}",
                            intent_type=intent_analysis.intent_category,
                            confidence_score=intent_analysis.confidence_score,
                            keywords=[intent_analysis.target_audience, intent_analysis.emotional_tone] if intent_analysis.target_audience and intent_analysis.emotional_tone else []
                        )
                        logger.info(f"Automatically forwarded blog seed and intent analysis to Redmine for hour_key: {hour_key}")
            except Exception as e:
                logger.error(f"Failed to automatically forward to Redmine: {e}")
                # 自動転送の失敗はブログ種生成の成功に影響しない

        return jsonify({
            "status": "success",
            "message": "Processing completed",
            "hour_key": hour_key
        }), 200

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return jsonify({"error": str(e)}), 500

@line_webhook_bp.route("/blog_seed/<hour_key>", methods=["GET"])
def get_blog_seed(hour_key: str):
    """生成されたブログ種を取得するエンドポイント"""
    try:
        manager = BlogSeedManager()
        seed = manager.get_seed(hour_key)
        if not seed:
            return jsonify({"error": "Blog seed not found"}), 404

        return jsonify({
            "status": "success",
            "hour_key": hour_key,
            "content": seed.markdown_content,
            "created_at": seed.created_at.isoformat(),
            "updated_at": seed.updated_at.isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Failed to get blog seed: {e}")
        return jsonify({"error": "Database error"}), 500

