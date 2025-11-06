from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from config import supabase
import os
from services.core import templates
from routes import admin, auth, dashboard, shortlink, pastelink, redirect_shortlink, redirect_pastelink

load_dotenv()
is_dev = os.getenv("ENV", "dev") == "dev"

app = FastAPI(
    title="Safelinku",
    docs_url="/docs" if is_dev else None,
    redoc_url="/redoc" if is_dev else None,
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.middleware("http")
async def add_user_role(request: Request, call_next):
    token = request.cookies.get("access_token")
    user = None
    is_admin = False
    if token:
        try:
            user = supabase.auth.get_user(token).user
            profile = supabase.table("user_profiles").select("role").eq("id", user.id).execute()
            if profile.data and profile.data[0].get("role") == "admin":
                is_admin = True
        except Exception:
            pass

    request.state.user = user
    request.state.is_admin = is_admin
    response = await call_next(request)
    return response


if is_dev:
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
else:
    origins = ["https://safelinku.site"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

app.add_middleware(SecurityHeadersMiddleware)


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