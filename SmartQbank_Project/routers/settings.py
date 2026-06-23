from fastapi import APIRouter, HTTPException
import config

router = APIRouter()

@router.get("/")
async def get_settings():
    return {
        "status": "ok",
        "message": "大模型 API 配置已内置于后端环境变量中。如需修改，请修改服务端的环境变量或 .env 文件。",
        "current_model": config.get_api_model(),
        "current_base_url": config.get_api_base_url()
    }
