from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from config import supabase
import random, string
from fastapi import Form

EARNING_PER_CLICK = 0.0008  # USD per klik

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

@app.get("/s/{code}", response_class=HTMLResponse)
async def redirect_link(request: Request, code: str):
    res = supabase.table("links").select("*").eq("short_code", code).single().execute()
    if not res.data:
        return HTMLResponse("<h3>Link not found</h3>")

    # update clicks dan earnings
    new_clicks = res.data["clicks"] + 1
    new_earnings = round(res.data.get("earnings", 0) + EARNING_PER_CLICK, 2)

    supabase.table("links").update({
        "clicks": new_clicks,
        "earnings": new_earnings
    }).eq("short_code", code).execute()

    return templates.TemplateResponse("ad.html", {
        "request": request,
        "original_url": res.data["original_url"]
    })


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register_post(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        # create user via Supabase Auth (service role key)
        user = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True  # Set to True if you want to auto-confirm the email
        })

        return RedirectResponse("/login", status_code=302)
    except Exception as e:
        return templates.TemplateResponse("register.html", {"request": request, "error": str(e)})

@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    # hapus cookie access_token
    response.delete_cookie("access_token")
    return response

MIN_WITHDRAW = 5.0  # minimal withdraw $5

@app.post("/withdraw")
async def withdraw(request: Request, amount: float = Form(...)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    # ambil user info
    user = supabase.auth.get_user(token)
    user_id = user.user.id

    # hitung total earnings user
    links = supabase.table("links").select("earnings").eq("user_id", user_id).execute().data
    total_earnings = sum(link['earnings'] for link in links)

    # validasi minimum withdraw
    if amount < MIN_WITHDRAW:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "links": links,
            "error": f"Minimal withdraw adalah ${MIN_WITHDRAW}"
        })

    # validasi tidak melebihi total earnings
    if amount > total_earnings:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "links": links,
            "error": f"Jumlah withdraw terlalu besar! Total earnings: ${total_earnings}"
        })

    # simpan request withdraw
    supabase.table("withdrawals").insert({
        "user_id": user_id,
        "amount": amount,
        "status": "pending"
    }).execute()

    # reset earnings user (opsional)
    for link in links:
        supabase.table("links").update({"earnings": 0}).eq("user_id", user_id).execute()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "links": links,
        "success": f"Withdraw request ${amount} berhasil dibuat! Status: pending"
    })
