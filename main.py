from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from config import supabase, EARNING_PER_CLICK
import random, string

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ========== UTIL ==========
def random_code(n=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

def get_user_profile(user_id):
    res = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
    if res.data:
        return res.data[0]
    return None


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
        response.set_cookie(key="access_token", value=session.access_token, httponly=True)
        return response
    except Exception as e:
        return templates.TemplateResponse("login.html", {"request": request, "error": str(e)})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    token = request.cookies.get("access_token")
    user = supabase.auth.get_user(token).user if token else None
    if not user:
        return RedirectResponse("/login")

    profile = get_user_profile(user.id)
    if not profile:
        return HTMLResponse("<h3>Profile not found</h3>")

    # ambil link milik user
    links = supabase.table("links").select("*").eq("user_id", user.id).execute().data

    total_clicks = sum(l["clicks"] for l in links)
    total_earnings = sum(l["earnings"] for l in links)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "profile": profile,
        "links": links,
        "total_clicks": total_clicks,
        "total_earnings": total_earnings,
        "total_links": len(links)
    })


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        print("❌ Tidak ada token")
        return RedirectResponse("/login")

    try:
        user = supabase.auth.get_user(token).user
    except Exception as e:
        print("❌ Gagal ambil user dari token:", e)
        return RedirectResponse("/login")

    try:
        profile = get_user_profile(user.id)
        if not profile:
            print("❌ Profil user tidak ditemukan")
            return HTMLResponse("<h3>Profile not found</h3>")
        if profile["role"] != "admin":
            print("❌ Bukan admin")
            return HTMLResponse("<h3>Access denied</h3>")

        # Ambil semua data
        users = supabase.table("user_profiles").select("*").execute().data
        links = supabase.table("links").select("*").execute().data
        withdrawals = supabase.table("withdrawals").select("*").execute().data

        # Statistik
        total_clicks = sum(link.get("clicks", 0) for link in links)
        total_earnings = sum(link.get("earnings", 0.0) for link in links)

        return templates.TemplateResponse("admin.html", {
            "request": request,
            "user": user,
            "users": users,
            "links": links,
            "withdrawals": withdrawals,
            "total_clicks": total_clicks,
            "total_earnings": total_earnings,
            "total_users": len(users),
            "total_links": len(links)
        })
    except Exception as e:
        print("❌ Error di route /admin:", e)
        return HTMLResponse(f"<h3>Internal error: {e}</h3>")


@app.post("/shorten")
async def shorten(request: Request, url: str = Form(...)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    user = supabase.auth.get_user(token)
    code = random_code()
    supabase.table("links").insert({"user_id": user.user.id, "original_url": url, "short_code": code}).execute() # type: ignore
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

@app.get("/withdraw", response_class=HTMLResponse)
def withdraw_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    user = supabase.auth.get_user(token).user
    profile = get_user_profile(user.id)
    if not profile:
        return RedirectResponse("/dashboard")

    # ambil balance (dari total link earnings misal)
    links = supabase.table("links").select("earnings").eq("user_id", user.id).execute().data
    total_earnings = sum(l.get("earnings", 0) for l in links)
    withdrawals = supabase.table("withdrawals").select("*").eq("user_id", user.id).execute().data
    withdrawn = sum(w.get("amount", 0) for w in withdrawals if w["status"] in ["pending", "approved"])
    balance = total_earnings - withdrawn

    return templates.TemplateResponse("withdraw.html", {
        "request": request,
        "user": user,
        "balance": balance,
        "withdrawals": withdrawals
    })

@app.post("/withdraw", response_class=HTMLResponse)
def withdraw_request(request: Request, paypal_email: str = Form(...), amount: float = Form(...)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    user = supabase.auth.get_user(token).user

    links = supabase.table("links").select("earnings").eq("user_id", user.id).execute().data
    total_earnings = sum(l.get("earnings", 0) for l in links)
    withdrawals = supabase.table("withdrawals").select("*").eq("user_id", user.id).execute().data
    withdrawn = sum(w.get("amount", 0) for w in withdrawals if w["status"] in ["pending", "approved"])
    balance = total_earnings - withdrawn

    # validasi
    if amount < 5:
        return HTMLResponse("<h3>❌ Minimal withdraw $5</h3>")
    if amount > balance:
        return HTMLResponse("<h3>❌ Saldo tidak cukup</h3>")

    # simpan permintaan withdraw
    supabase.table("withdrawals").insert({
        "user_id": user.id,
        "amount": amount,
        "paypal_email": paypal_email,
        "status": "pending"
    }).execute()

    # update last_withdraw di profile
    supabase.table("user_profiles").update({
        "last_withdraw": datetime.utcnow().isoformat()
    }).eq("id", user.id).execute()

    return RedirectResponse("/withdraw", status_code=302)

@app.get("/admin/withdrawals", response_class=HTMLResponse)
def admin_withdrawals(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    user = supabase.auth.get_user(token).user
    profile = get_user_profile(user.id)
    if not profile or profile["role"] != "admin":
        return HTMLResponse("<h3>Access denied</h3>")

    withdrawals = supabase.table("withdrawals").select("*").order("created_at", desc=True).execute().data
    return templates.TemplateResponse("admin_withdrawals.html", {
        "request": request,
        "withdrawals": withdrawals
    })

@app.post("/admin/withdrawals/update", response_class=HTMLResponse)
def update_withdraw_status(request: Request, withdraw_id: int = Form(...), action: str = Form(...)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    user = supabase.auth.get_user(token).user
    profile = get_user_profile(user.id)
    if not profile or profile["role"] != "admin":
        return HTMLResponse("<h3>Access denied</h3>")

    new_status = "approved" if action == "approve" else "rejected"
    supabase.table("withdrawals").update({"status": new_status}).eq("id", withdraw_id).execute()
    if new_status == "approved":
        wd = supabase.table("withdrawals").select("*").eq("id", withdraw_id).execute().data[0]
        user_id = wd["user_id"]
        amount = float(wd["amount"])

        # update saldo user (jika kamu pakai kolom balance)
        profile = get_user_profile(user_id)
        new_balance = max(0, (profile.get("balance") or 0) - amount)
        supabase.table("user_profiles").update({"balance": new_balance}).eq("id", user_id).execute()


    return RedirectResponse("/admin/withdrawals", status_code=302)
