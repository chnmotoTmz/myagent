from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any

from redmine_tool import create_issue, RedmineError
from tool_manifests import TOOL_MANIFESTS

app = FastAPI(
    title="Redmine MCP Tool Server",
    description="Provides MCP-compliant tools for interacting with Redmine.",
    version="1.0.0"
)

@app.get("/tool/manifests")
async def get_tool_manifests():
    return JSONResponse(content=TOOL_MANIFESTS)

@app.post("/tool/{tool_name}")
async def handle_tool_call(tool_name: str, request: Request):
    body = await request.json()
    params = body.get("params", {})

    if tool_name == "create_issue":
        try:
            if not all(k in params for k in ["project_id", "subject", "description"]):
                raise HTTPException(status_code=400, 
                                  detail="Missing required parameters: project_id, subject, description")

            result = create_issue(
                project_id=params["project_id"],
                subject=params["subject"],
                description=params["description"],
                tracker_id=params.get("tracker_id", 1)
            )
            return JSONResponse(content={"success": True, "data": result})
        except RedmineError as e:
            return JSONResponse(
                status_code=e.status_code or 500,
                content={"success": False, "error": str(e), "details": e.response_data}
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": f"Internal server error: {str(e)}"}
            )
    else:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")

@app.get("/")
async def read_root():
    return {"message": "Redmine MCP Tool Server is running. Visit /docs for API documentation."}
