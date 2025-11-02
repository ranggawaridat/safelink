from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from config import supabase
from services.user_service import get_user_profile

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["Withdraws"])


@router.get("/withdraw", response_class=HTMLResponse)
def withdraw_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    try:
        user = supabase.auth.get_user(token).user
    except Exception:
        return RedirectResponse("/login")
    
    profile = get_user_profile(user.id)
    if not profile:
        return RedirectResponse("/dashboard")

    # hitung saldo user
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

@router.post("/withdraw", response_class=HTMLResponse)
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

@router.get("/admin/withdrawals", response_class=HTMLResponse)
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


@router.post("/admin/withdrawals/update", response_class=HTMLResponse)
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
