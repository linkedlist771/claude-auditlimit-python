import argparse
import fire
import uvicorn
from fastapi import FastAPI
from loguru import logger
from claude_auditlimit_python.configs import LOGS_PATH
from claude_auditlimit_python.lifespan import lifespan
from claude_auditlimit_python.middlewares.register_middlewares import (
    register_middleware,
)
from claude_auditlimit_python.router import router

parser = argparse.ArgumentParser()
parser.add_argument("--host", default="0.0.0.0", help="host")
parser.add_argument("--port", default=8000, help="port")
parser.add_argument("--workers", default=1, type=int, help="workers")
args = parser.parse_args()
logger.add(LOGS_PATH / "log_file.log", rotation="1 week")  # 每周轮换一次文件
app = FastAPI(lifespan=lifespan)
app = register_middleware(app)


def start_server(port=args.port, host=args.host):
    logger.info(f"Starting server at {host}:{port}")
    app.include_router(router)
    config = uvicorn.Config(app, host=host, port=port, workers=args.workers)
    server = uvicorn.Server(config=config)
    try:
        server.run()
    finally:
        logger.info("Server shutdown.")


if __name__ == "__main__":
    fire.Fire(start_server)
