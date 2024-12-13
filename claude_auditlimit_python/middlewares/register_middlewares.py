from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

from claude_auditlimit_python.configs import IP_REQUEST_LIMIT_PER_MINUTE
from claude_auditlimit_python.middlewares.docs_middleware import (
    ApidocBasicAuthMiddleware,
)
from claude_auditlimit_python.middlewares.not_found_middleware import (
    NotFoundResponseMiddleware,
)
from claude_auditlimit_python.middlewares.rate_limiter_middleware import (
    RateLimitMiddleware,
)


def register_cross_origin(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


def register_docs_auth(app: FastAPI):

    # app_env = 'production'
    # if app_env == 'production':
    @app.get("/docs", include_in_schema=False)
    async def get_swagger_documentation():
        return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")

    @app.get("/redoc", include_in_schema=False)
    async def get_redoc_documentation():
        return get_redoc_html(openapi_url="/openapi.json", title="docs")

    @app.get("/openapi.json", include_in_schema=False)
    async def get_openapi_json():
        return get_openapi(title="FastAPI", version="0.1.0", routes=app.routes)

    app.add_middleware(ApidocBasicAuthMiddleware)
    return app


def register_middleware(app: FastAPI):
    app = register_cross_origin(app)
    app = register_docs_auth(app)
    # app.add_middleware(NotFoundResponseMiddleware)
    # app.add_middleware(RateLimitMiddleware, rate_per_minute=IP_REQUEST_LIMIT_PER_MINUTE)
    return app
