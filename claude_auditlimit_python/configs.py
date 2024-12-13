from httpx import Timeout
from pathlib import Path
import os

API_KEY_REFRESH_INTERVAL_HOURS = 3

API_KEY_REFRESH_INTERVAL = API_KEY_REFRESH_INTERVAL_HOURS * 60 * 60
BASIC_KEY_MAX_USAGE = 10
PLUS_KEY_MAX_USAGE = 60

ACCOUNT_DELETE_LIMIT = 150000  # 暂时先不删除了


STREAM_CONNECTION_TIME_OUT = 60
STREAM_READ_TIME_OUT = 60


STREAM_POOL_TIME_OUT = 10 * 60


NEW_CONVERSATION_RETRY = 5

# 设置连接超时为你的 STREAM_CONNECTION_TIME_OUT，其他超时设置为无限
STREAM_TIMEOUT = Timeout(
    connect=STREAM_CONNECTION_TIME_OUT,  # 例如设为 10 秒
    read=STREAM_READ_TIME_OUT,  # 例如设为 5 秒
    write=None,
    pool=STREAM_POOL_TIME_OUT,  # 例如设为 10 分钟
)

USE_PROXY = False
USE_MERMAID_AND_SVG = True

PROXIES = {"http://": "socks5://127.0.0.1:7891", "https://": "socks5://127.0.0.1:7891"}

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))


DOCS_USERNAME = "claude-backend"
DOCS_PASSWORD = "20Wd!!!!"


# Claude 官方镜像的链接w

CLAUDE_OFFICIAL_REVERSE_BASE_URL: str = (
    "http://ai.liuli.585dg.com"  #     "https://demo.fuclaude.com"  #
)

# 三小时
CLAUDE_OFFICIAL_EXPIRE_TIME = 3 * 60 * 60


# 每次使用都会增加20次次数
CLAUDE_OFFICIAL_USAGE_INCREASE = 5


# limits check的函数
CLAUDE_CLIENT_LIMIT_CHECKS_INTERVAL_MINUTES = 60
CLAUDE_CLIENT_LIMIT_CHECKS_PROMPT = "Say: OK."


# IP访问的限制
IP_REQUEST_LIMIT_PER_MINUTE = 40  # 一分钟40次

# ROOT path
ROOT = Path(__file__).parent.parent

LOGS_PATH = ROOT / "logs"

MAX_DEVICES = 3

LOGS_PATH.mkdir(exist_ok=True)

if __name__ == "__main__":
    print(ROOT)
