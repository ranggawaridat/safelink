from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import os
from routes import admin, auth, dashboard, shortlink, pastelink, redirect_shortlink, redirect_pastelink

# --- Load environment (.env) ---
load_dotenv()
is_dev = os.getenv("ENV", "dev") == "dev"


app = FastAPI(
    title="Safelinku",
    docs_url="/docs" if is_dev else None,
    redoc_url="/redoc" if is_dev else None,
)

# Static files (jika kamu punya folder css/js di /static)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


# --- CORS Middleware (opsional tapi penting) ---
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


# --- Security Headers Middleware ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Daftarkan semua router tanpa prefix agar endpoint sesuai rencana
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(shortlink.router)
app.include_router(pastelink.router)
app.include_router(redirect_shortlink.router)
app.include_router(redirect_pastelink.router)
app.include_router(admin.router)

# Root redirect ke /dashboard jika login, atau ke /login
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})