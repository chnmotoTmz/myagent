"""
Redmineチケット管理エージェント - メインアプリケーション

Redmineチケット管理エージェントのWebアプリケーションエントリーポイント。
"""

import os
import json
import logging
import asyncio
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, time
import uvicorn
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Body, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# カスタムログユーティリティをインポート
from .log_utils import setup_logging

# ロギングの設定 (カスタムハンドラーで安全なUnicode対応)
setup_logging(log_file="logs/redmine_agent.log", level=logging.INFO)
logger = logging.getLogger(__name__)

from .core import RedmineAgent
from .linebot_adapter import LineBotAdapter
from .scheduler import start_scheduler, schedule_daily_tasks

# LLMのインポート状態をチェック
import importlib.util
LLM_AVAILABLE = False
LLM_READY = False

if importlib.util.find_spec("google.generativeai") is not None:
    LLM_AVAILABLE = True
    try:
        from .llm_helper import RedmineAssistant
        LLM_READY = True
    except (ImportError, ModuleNotFoundError) as e:
        LLM_READY = False
        logger.warning(f"LLM助手モジュールをインポートできませんでした: {str(e)}")
logger = logging.getLogger(__name__)

# .envファイルの読み込み
load_dotenv()

# 設定モジュールのインポート
from .config import get_config, set_config

# 環境変数からの設定読み込み
REDMINE_URL = os.getenv("REDMINE_URL", "http://localhost:3000")
REDMINE_API_KEY = os.getenv("REDMINE_API_KEY", "dummy_api_key_for_development")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "dummy_line_token_for_development")
USER_ID_MAPPING = json.loads(os.getenv("USER_ID_MAPPING", '{"1": "U0082f5630775769cb2655fb503e958bb"}'))

# 初期化
redmine_agent = RedmineAgent(
    redmine_url=REDMINE_URL,
    api_key=REDMINE_API_KEY
)

# LINE adapterを初期化
# 本番環境ではLINE BOT SDKのインストールが必要
try:
    line_adapter = LineBotAdapter(
        line_token=LINE_TOKEN,
        redmine_agent=redmine_agent
    )
    logger.info("LINE Bot adapter initialized in simplified mode")
except Exception as e:
    logger.error(f"Failed to initialize LINE Bot adapter: {e}")
    line_adapter = None

# スケジューラータスクのハンドル
scheduler_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクルを管理"""
    # Startup
    global scheduler_task
    if line_adapter:
        scheduler_task = asyncio.create_task(
            start_scheduler(
                line_adapter=line_adapter,
                redmine_agent=redmine_agent,
                user_id_mapping=USER_ID_MAPPING
            )
        )
        logger.info("Started scheduler task")
    
    yield
    
    # Shutdown
    if scheduler_task:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        logger.info("Shutdown: Scheduler task cancelled")

app = FastAPI(
    title="Redmine Agent",
    description="Redmineチケット管理エージェントAPI",
    version="1.0.0",
    lifespan=lifespan
)

# CORSミドルウェア設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LineWebhookRequest(BaseModel):
    user: str
    type: str
    messageId: Optional[str] = None
    message: Optional[str] = None

@app.get("/")
async def root():
    """ルートエンドポイント - ヘルスチェック"""
    return {"status": "ok", "message": "Redmine Agent is running"}

@app.post("/api/webhook/line")
async def line_webhook(request: LineWebhookRequest, background_tasks: BackgroundTasks):
    """LINE Webhookエンドポイント"""
    logger.info(f"Received webhook: {request.dict()}")
    
    if not line_adapter:
        logger.error("LINE adapter is not initialized")
        raise HTTPException(status_code=500, detail="LINE integration not configured")
    
    user_id = request.user
    message_type = request.type
    
    if message_type != "text":
        return {
            "status": "ignored",
            "message": f"Message type {message_type} is not supported"
        }
    
    if not request.message:
        raise HTTPException(status_code=400, detail="Message content is required for text messages")
    
    # 応答メッセージを生成
    response_text = line_adapter.handle_message(request.message, user_id)
    
    # 非同期でメッセージを送信
    background_tasks.add_task(
        line_adapter.send_message,
        user_id,
        response_text
    )
    
    return {"status": "ok", "message": "Message processed"}

@app.post("/api/receive_message")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    try:
        # リクエストログの記録
        request_data = await request.json()
        logger.info(f"Received message data: {request_data}")
        
        # フィールド名の変換
        processed_request = {
            "user_id": request_data.get("user_id"),
            "content": request_data.get("message_text"),  # message_text を content として扱う
            "timestamp": request_data.get("timestamp"),
            "source_type": request_data.get("source_type")
        }
        
        # 必須フィールドの検証
        if not processed_request["user_id"] or not processed_request["content"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid request. 'user_id' and 'content' fields are required"
            )
        
        # 以降の処理は processed_request を使用
        user_id = processed_request["user_id"]
        message_text = processed_request["content"]
        
        if not line_adapter:
            logger.error("LINE adapter is not initialized")
            raise HTTPException(status_code=500, detail="LINE integration not configured")
        
        # メッセージを処理
        response_text = line_adapter.handle_message(message_text, user_id)
        
        # 応答を送信
        background_tasks.add_task(
            line_adapter.send_message,
            user_id,
            response_text
        )
        
        return {"status": "ok", "message": "Message processed successfully"}
        
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/send_morning_report")
async def send_morning_report(background_tasks: BackgroundTasks):
    """朝のレポートを手動で送信（テスト用）"""
    if not line_adapter or not USER_ID_MAPPING:
        raise HTTPException(status_code=500, detail="LINE integration not configured properly")
    
    for redmine_user_id, line_user_id in USER_ID_MAPPING.items():
        try:
            tasks = redmine_agent.get_daily_tasks(user_id=int(redmine_user_id))
            report = redmine_agent.format_morning_report(tasks)
            
            background_tasks.add_task(
                line_adapter.send_message,
                line_user_id,
                report
            )
            
            logger.info(f"Morning report scheduled for LINE user {line_user_id}")
        except Exception as e:
            logger.error(f"Error sending morning report: {e}", exc_info=True)
    
    return {"status": "ok", "message": "Morning reports scheduled"}

@app.post("/api/send_evening_report")
async def send_evening_report(background_tasks: BackgroundTasks):
    """夜のレポートを手動で送信（テスト用）"""
    if not line_adapter or not USER_ID_MAPPING:
        raise HTTPException(status_code=500, detail="LINE integration not configured properly")
    
    today = datetime.today().date().isoformat()
    
    for redmine_user_id, line_user_id in USER_ID_MAPPING.items():
        try:
            # 今日の作業時間を取得
            time_entries = redmine_agent.get_time_entries(
                user_id=int(redmine_user_id),
                from_date=today,
                to_date=today
            )
            
            # 完了したタスク
            completed_tasks = []
            
            report = redmine_agent.format_evening_report(completed_tasks, time_entries)
            
            background_tasks.add_task(
                line_adapter.send_message,
                line_user_id,
                report
            )
            
            logger.info(f"Evening report scheduled for LINE user {line_user_id}")
        except Exception as e:
            logger.error(f"Error sending evening report: {e}", exc_info=True)
    
    return {"status": "ok", "message": "Evening reports scheduled"}

@app.get("/api/tasks/daily")
async def get_daily_tasks(user_id: Optional[int] = None):
    """本日のタスクを取得"""
    try:
        tasks = redmine_agent.get_daily_tasks(user_id=user_id)
        return {"tasks": tasks}
    except Exception as e:
        logger.error(f"Error getting daily tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/upcoming")
async def get_upcoming_tasks(days: int = 7, user_id: Optional[int] = None):
    """今後のタスクを取得"""
    try:
        tasks = redmine_agent.get_upcoming_tasks(days=days, user_id=user_id)
        return {"tasks": tasks}
    except Exception as e:
        logger.error(f"Error getting upcoming tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summary/{issue_id}")
async def get_issue_summary(issue_id: int):
    """チケットの要約を取得"""
    try:
        summary = redmine_agent.summarize_ticket_history(issue_id)
        if "error" in summary:
            raise HTTPException(status_code=404, detail=summary["error"])
        return summary
    except Exception as e:
        logger.error(f"Error getting issue summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analyze/urgency/{issue_id}")
async def analyze_ticket_urgency(issue_id: int):
    """チケットの緊急度を分析（LLM機能）"""
    try:
        # チケットの情報を取得
        response = requests.get(
            f"{REDMINE_URL}/issues/{issue_id}.json",
            headers={"X-Redmine-API-Key": REDMINE_API_KEY, "Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail=f"チケット #{issue_id} が見つかりません")
            
        issue_data = response.json().get("issue", {})
        
        # LLM機能が有効か確認
        if not LLM_READY:
            raise HTTPException(status_code=400, detail="LLM機能が利用できません")
        
        # 緊急度分析
        llm_assistant = RedmineAssistant()
        urgency_data = llm_assistant.evaluate_ticket_urgency(issue_data)
        
        # 基本情報を追加
        result = {
            "issue_id": issue_id,
            "subject": issue_data.get("subject", ""),
            "status": issue_data.get("status", {}).get("name", ""),
            "priority": issue_data.get("priority", {}).get("name", ""),
            "urgency_analysis": urgency_data
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing ticket urgency: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/optimize")
async def get_optimization_suggestions():
    """タスク最適化の提案を取得"""
    try:
        suggestions = redmine_agent.suggest_task_consolidation()
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error getting optimization suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

class TimeEntryRequest(BaseModel):
    issue_id: int
    hours: float
    comments: str
    spent_on: Optional[str] = None

@app.post("/api/time_entries")
async def create_time_entry(request: TimeEntryRequest):
    """作業時間を登録"""
    try:
        success = redmine_agent.log_time_entry(
            issue_id=request.issue_id,
            hours=request.hours,
            comments=request.comments,
            spent_on=request.spent_on
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create time entry")
            
        return {"status": "ok", "message": "Time entry created successfully"}
    except Exception as e:
        logger.error(f"Error creating time entry: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

class UpdateIssueRequest(BaseModel):
    issue_id: int
    status_id: Optional[int] = None
    done_ratio: Optional[int] = None
    notes: Optional[str] = None

@app.put("/api/issues/{issue_id}")
async def update_issue(issue_id: int, request: UpdateIssueRequest):
    """チケットを更新"""
    try:
        success = True
        
        if request.status_id is not None:
            status_success = redmine_agent.update_issue_status(
                issue_id=issue_id,
                status_id=request.status_id,
                notes=request.notes
            )
            success = success and status_success
        
        if request.done_ratio is not None:
            progress_success = redmine_agent.update_issue_progress(
                issue_id=issue_id,
                done_ratio=request.done_ratio,
                notes=request.notes
            )
            success = success and progress_success
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update issue")
            
        return {"status": "ok", "message": "Issue updated successfully"}
    except Exception as e:
        logger.error(f"Error updating issue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# LLM設定用のモデル
class LlmConfigRequest(BaseModel):
    api_key: Optional[str] = None
    enable: bool = True

@app.get("/api/llm/status")
async def get_llm_status():
    """LLM機能のステータス確認"""
    try:
        result = {
            "llm_available": LLM_AVAILABLE,
            "llm_ready": LLM_READY
        }
        
        if LLM_READY:
            try:
                # LLM機能がインポートされていれば、APIキーの状態も確認
                llm_assistant = RedmineAssistant()
                result["api_connected"] = llm_assistant._test_api_connection()
                result["api_keys_count"] = len(llm_assistant.api_keys)
            except Exception as e:
                result["api_connected"] = False
                result["error"] = str(e)
        
        return result
    except Exception as e:
        logger.error(f"Error getting LLM status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/llm/config")
async def configure_llm(config: LlmConfigRequest):
    """LLM機能の設定"""
    try:
        result = {"status": "error", "message": "LLM機能を設定できません"}
        
        if not LLM_READY:
            raise HTTPException(status_code=400, detail="LLM機能がインストールされていません")
            
        # API鍵の設定/更新
        if config.api_key:
            # 簡易的な保存方法として.envファイルを更新
            # 実際のプロダクションでは、より安全な手段を検討すべき
            from dotenv import set_key
            set_key(".env", "GEMINI_API_KEY", config.api_key)
            logger.info("新しいGemini APIキーが設定されました")
            
            # 即時反映
            os.environ["GEMINI_API_KEY"] = config.api_key
            
            # 動作確認
            try:
                llm_assistant = RedmineAssistant(api_key=config.api_key)
                if llm_assistant._test_api_connection():
                    result = {"status": "success", "message": "APIキーの設定と接続テストに成功しました"}
                else:
                    result = {"status": "warning", "message": "APIキーを設定しましたが、接続テストに失敗しました"}
            except Exception as e:
                result = {"status": "error", "message": f"APIキーの検証中にエラー: {str(e)}"}
        else:
            result = {"status": "success", "message": "設定を更新しました"}
            
        return result
        
    except Exception as e:
        logger.error(f"Error configuring LLM: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/mode")
async def change_mode(mode_request: Dict[str, Any]):
    """
    システムモード（開発/本番）を切り替える
    """
    try:
        mode = mode_request.get("mode")
        if not mode or mode not in ["dev", "prod"]:
            raise HTTPException(status_code=400, detail="Invalid mode. Use 'dev' or 'prod'")
            
        # .envファイルの更新
        from dotenv import set_key
        
        is_dev_mode = mode == "dev"
        set_key(".env", "DEBUG", str(is_dev_mode))
        
        # ログレベルの更新
        log_level = "DEBUG" if is_dev_mode else "INFO"
        set_key(".env", "LOG_LEVEL", log_level)
        
        # 設定の更新
        set_config("system.environment", "development" if is_dev_mode else "production")
        set_config("system.debug_mode", is_dev_mode)
        
        # アプリケーションに反映
        mode_name = "開発モード" if is_dev_mode else "本番モード"
        logger.info(f"システム動作モードを {mode_name} に変更しました")
        
        return {
            "status": "success", 
            "message": f"システム動作モードを {mode_name} に変更しました",
            "mode": mode,
            "debug": is_dev_mode
        }
    
    except Exception as e:
        logger.error(f"モード変更中にエラーが発生しました: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True
    )
