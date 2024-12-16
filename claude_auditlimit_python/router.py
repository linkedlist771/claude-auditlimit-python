# router.py
from json import JSONDecodeError
from loguru import logger

from fastapi import APIRouter, HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse

from datetime import datetime

from claude_auditlimit_python.configs import MAX_DEVICES, RATE_LIMIT
from claude_auditlimit_python.redis_manager.device_manager import DeviceManager
from claude_auditlimit_python.redis_manager.usage_manager import UsageManager
from claude_auditlimit_python.utils.api_key_utils import remove_beamer

router = APIRouter()


@router.get("/")
async def _():
    return "Hi this is from claude audit limit python-version"


@router.api_route("/audit_limit", methods=["GET", "POST"])
async def audit_limit(request: Request):
    api_key = request.headers.get("Authorization", None)
    host = (
        request.headers.get("X-Forwarded-Host")
        if request.headers.get("X-Forwarded-Host", None)
        else request.url.hostname
    )
    api_key = remove_beamer(api_key)
    # "User-Agent"
    user_agent = request.headers.get("User-Agent")
    if not host or not user_agent:
        raise HTTPException(status_code=400, detail="Host and User-Agent are required")

    # Check device authorization
    device_manager = DeviceManager()
    device_identifier = user_agent  # Using user agent as device identifier

    try:
        allowed = await device_manager.check_and_add_device(
            token=api_key,
            device_identifier=device_identifier,
            user_agent=user_agent,
            host=host,
        )

        if not allowed:
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "message": f"Maximum number of devices ({MAX_DEVICES}) reached. Please logout from another device first.\n"
                        f"已达到最大设备数 ({MAX_DEVICES})。请先从另一台设备注销。"
                    }
                },
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": {"message": f"Failed to verify device\n无法验证设备"}},
        )
    # 获取请求内容
    try:
        request_data = await request.json()
        # 获取 action - 判断请求类型
        action = request_data.get("action", "")

        # 获取 model - 模型名称
        model = request_data.get("model", "")

        # 获取 prompt - 输入内容
        # 处理嵌套的字典结构
        messages = request_data.get("messages", [])
        prompt = ""
        if messages and len(messages) > 0:
            content = messages[0].get("content", {})
            if isinstance(content, dict) and "parts" in content:
                parts = content.get("parts", [])
                if parts and len(parts) > 0:
                    prompt = parts[0]
        if "claude" in model.lower():
            # Initialize usage manager
            usage_manager = UsageManager()  # Configure host as needed
            try:
                # Get current usage stats
                stats = await usage_manager.get_token_usage(api_key)
                # Get configured limit from settings
                # Check 3-hour usage limit
                used_3h = stats.last_3_hours
                remaining = RATE_LIMIT - used_3h
                if remaining <= 0:
                    # Calculate wait time
                    redis = await usage_manager.get_aioredis()
                    key = usage_manager._get_redis_key(
                        api_key, usage_manager.PERIOD_3HOURS
                    )
                    ttl = await redis.ttl(key)

                    wait_seconds = max(ttl, 0)

                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": {
                                "message": f"Usage limit exceeded. Current limit is {RATE_LIMIT} "
                                f"requests per 3 hours. Please wait {wait_seconds} seconds. "
                                f"您已触发使用频率限制，当前限制为{RATE_LIMIT}次/3小时，"
                                f"请等待{wait_seconds}秒后重试。"
                            }
                        },
                    )

                # Increment usage if within limits
                await usage_manager.increment_token_usage(api_key)

                # return JSONResponse(
                #     status_code=200,
                #     content={
                #         "message": "Request authorized",
                #         "remaining": remaining - 1,
                #     },
                # )
                return
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Error checking usage limits: {str(e)}"
                )

    except JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON data")

    return


@router.get("/token_stats")
async def token_stats(request: Request):
    try:
        # Initialize usage manager
        usage_manager = UsageManager()

        # Get all token usage statistics
        usage_stats = await usage_manager.get_all_token_usage()
        logger.debug(usage_stats)
        # Get current time
        now = datetime.now()

        # Prepare response data
        stats = []

        # Process usage stats
        for token, usage in usage_stats.items():
            # 硬编码 active 和 last_seen
            stat = {
                "token": token,
                "usage": {
                    "total": usage.total,
                    "last_3_hours": usage.last_3_hours,
                    "last_12_hours": usage.last_12_hours,
                    "last_24_hours": usage.last_24_hours,
                    "last_week": usage.last_week,
                },
                "current_active": True,  # 硬编码为 True
                "last_seen_seconds": 60,  # 硬编码为60秒
            }
            stats.append(stat)

        # Sort by total usage in descending order
        stats.sort(key=lambda x: x["usage"]["total"], reverse=True)

        return JSONResponse(content={"code": 0, "msg": "success", "data": stats})

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "msg": "Failed to get token statistics",
                "error": str(e),
            },
        )


# Update the router.py file with these new endpoints


@router.get("/devices")
async def devices(request: Request):
    api_key = request.headers.get("Authorization")
    if api_key:
        api_key = remove_beamer(api_key)

    device_manager = DeviceManager()
    device_list = await device_manager.get_device_list(api_key)

    return JSONResponse(
        content={
            "code": 0,
            "msg": "Success",
            "data": {
                "devices": [device.to_dict() for device in device_list],
                "total": len(device_list),
            },
        }
    )


@router.get("/logout")
async def logout(request: Request):
    try:
        api_key = request.headers.get("Authorization")
        if api_key:
            api_key = remove_beamer(api_key)

        host = (
            request.headers.get("X-Forwarded-Host")
            if request.headers.get("X-Forwarded-Host")
            else request.url.hostname
        )
        user_agent = request.headers.get("User-Agent")

        if not host or not user_agent:
            raise HTTPException(
                status_code=400, detail="Host and User-Agent are required"
            )

        device_identifier = user_agent
        device_manager = DeviceManager()
        success = await device_manager.remove_device(api_key, device_identifier)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to logout device")

        return JSONResponse(
            content={"code": 0, "msg": "Device logged out successfully"}
        )
    except:
        from traceback import format_exc

        logger.error(format_exc())


@router.get("/all_token_devices")
async def all_token_devices(request: Request):
    device_manager = DeviceManager()
    all_devices = await device_manager.get_all_token_devices()

    stats = []
    for token, devices in all_devices.items():
        stat = {
            "token": token,
            "devices": [device.to_dict() for device in devices],
            "total": len(devices),
        }
        stats.append(stat)

    # Sort by total number of devices
    stats.sort(key=lambda x: x["total"], reverse=True)

    return JSONResponse(content={"code": 0, "msg": "Success", "data": stats})
