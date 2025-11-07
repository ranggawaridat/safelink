from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
from services.core import templates
from routes import admin, auth, dashboard, shortlink, pastelink, redirect_shortlink, redirect_pastelink
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware


load_dotenv()
is_dev = os.getenv("ENV", "dev") == "dev"
    
app = FastAPI(
    title="Safelinku",
    docs_url="/docs" if is_dev else None,
    redoc_url="/redoc" if is_dev else None,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(HTTPSRedirectMiddleware)

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