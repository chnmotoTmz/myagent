"""
ブログ記事の意図分析に関連するAPI
"""
import logging
from flask import Blueprint, request, jsonify

from src.database import db
from src.models.blog_intent import BlogIntentAnalysis
from src.services.intent_analyzer import IntentAnalysisManager
from src.services.redmine_integration import RedmineIntegrationService
import src.config as config

# ロギング設定
logger = logging.getLogger(__name__)

# Blueprint定義
blog_intent_bp = Blueprint("blog_intent", __name__, url_prefix="/api/webhook")

@blog_intent_bp.route("/blog_intent/<hour_key>", methods=["GET", "POST"])
def analyze_blog_intent(hour_key):
    """ブログ記事の意図を分析するエンドポイント
    
    GET: 既存の分析結果を取得
    POST: 新規に分析を実行
    """
    try:
        # GETリクエスト - 既存の分析結果を返す
        if request.method == "GET":
            analysis = BlogIntentAnalysis.query.filter_by(hour_key=hour_key).first()
            if not analysis:
                return jsonify({
                    "status": "error",
                    "message": f"Intent analysis not found for hour_key: {hour_key}"
                }), 404
                
            return jsonify({
                "status": "success",
                "data": analysis.to_dict()
            }), 200
        
        # POSTリクエスト - 新規に分析を実行
        manager = IntentAnalysisManager()
        analysis = manager.analyze_intent(hour_key)
        
        if not analysis:
            return jsonify({
                "status": "error",
                "message": f"Failed to analyze intent for hour_key: {hour_key}"
            }), 500
            
        return jsonify({
            "status": "success",
            "message": "Intent analysis completed",
            "data": analysis.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error in blog intent analysis endpoint: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500

@blog_intent_bp.route("/forward_to_redmine/<hour_key>", methods=["POST"])
def forward_to_redmine(hour_key):
    """分析結果をRedmineチケット管理エージェントに転送する"""
    if not config.REDMINE_INTEGRATION_ENABLED:
        return jsonify({
            "status": "error",
            "message": "Redmine integration is disabled"
        }), 400
    
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id")
        
        if not user_id:
            return jsonify({
                "status": "error",
                "message": "user_id is required in request body"
            }), 400
            
        # 分析結果の取得
        analysis = BlogIntentAnalysis.query.filter_by(hour_key=hour_key).first()
        if not analysis:
            return jsonify({
                "status": "error",
                "message": f"Intent analysis not found for hour_key: {hour_key}"
            }), 404
            
        # BlogSeedの取得
        from src.routes.line_webhook import BlogSeedManager
        blog_seed = BlogSeedManager.get_seed(hour_key)
        if not blog_seed:
            return jsonify({
                "status": "error",
                "message": f"Blog seed not found for hour_key: {hour_key}"
            }), 404
            
        # Redmine連携サービスのインスタンス化
        redmine_service = RedmineIntegrationService()
        
        # Redmineチケット管理エージェントにデータを転送
        result = redmine_service.process_message_with_intent(
            user_id=user_id,
            message_text=f"ブログ記事の意図分析結果: {analysis.intent_category}",
            intent_type=analysis.intent_category,
            confidence_score=analysis.confidence_score,
            keywords=[analysis.target_audience, analysis.emotional_tone] if analysis.target_audience and analysis.emotional_tone else []
        )
        
        return jsonify({
            "status": "success",
            "message": "Intent analysis forwarded to Redmine",
            "redmine_response": result
        }), 200
        
    except Exception as e:
        logger.error(f"Error forwarding to Redmine: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500