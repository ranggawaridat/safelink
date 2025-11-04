from fastapi import FastAPI, Request, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

from routes import admin, auth, dashboard, shortlink, pastelink, redirect_shortlink, redirect_pastelink

app = FastAPI(title="SafeLinku", version="1.0")


# Static files (jika kamu punya folder css/js di /static)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

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