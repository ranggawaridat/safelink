from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from config import supabase
import random, string

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ========== UTIL ==========
def random_code(n=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


# ========== ROUTES ==========

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        auth = supabase.auth.sign_in_with_password({"email": email, "password": password})
        session = auth.session
        response = RedirectResponse("/dashboard", status_code=302)
        response.set_cookie(key="access_token", value=session.access_token)
        return response
    except Exception as e:
        return templates.TemplateResponse("login.html", {"request": request, "error": str(e)})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    user = supabase.auth.get_user(token)
    data = (
        supabase.table("links")
        .select("*")
        .eq("user_id", user.user.id)
        .execute()
    )
    return templates.TemplateResponse("dashboard.html", {"request": request, "links": data.data})


@app.post("/shorten")
async def shorten(request: Request, url: str = Form(...)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    user = supabase.auth.get_user(token)
    code = random_code()
    supabase.table("links").insert({"user_id": user.user.id, "original_url": url, "short_code": code}).execute()
    return RedirectResponse("/dashboard", status_code=302)


@app.get("/s/{code}")
async def redirect_link(code: str):
    res = supabase.table("links").select("*").eq("short_code", code).single().execute()
    if not res.data:
        return HTMLResponse("<h3>Link not found</h3>")
    url = res.data["original_url"]
    supabase.table("links").update({"clicks": res.data["clicks"] + 1}).eq("short_code", code).execute()
    return RedirectResponse(url)
