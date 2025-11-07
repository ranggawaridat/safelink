from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
from services.core import templates
from routes import admin, auth, dashboard, shortlink, pastelink, redirect_shortlink, redirect_pastelink
from starlette.responses import Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

try:
    from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
except Exception:
    # Fallback no-op ProxyHeadersMiddleware for environments where
    # starlette.middleware.proxy_headers is not available.
    from starlette.middleware.base import BaseHTTPMiddleware

    class ProxyHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            return await call_next(request)


load_dotenv()
is_dev = os.getenv("ENV", "dev") == "dev"

allowed_hosts = ["safelinku.site", "*.safelinku.site"]
if is_dev:
    allowed_hosts += ["localhost", "127.0.0.1"]

    
app = FastAPI(
    title="Safelinku",
    docs_url="/docs" if is_dev else None,
    redoc_url="/redoc" if is_dev else None,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.middleware("http")
async def hsts_middleware(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

app.add_middleware(ProxyHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(shortlink.router)
app.include_router(pastelink.router)
app.include_router(redirect_shortlink.router)
app.include_router(redirect_pastelink.router)
app.include_router(admin.router)


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})