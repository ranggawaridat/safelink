from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from config import supabase

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)

    try:
        user = supabase.auth.get_user(token).user
    except Exception:
        return RedirectResponse("/login", status_code=302)

    # Ambil semua shortlink dan pastelink milik user
    links = supabase.table("links").select("*").eq("user_id", user.id).execute().data or []
    pastes = supabase.table("pastes").select("*").eq("user_id", user.id).execute().data or []

    # Hitung total klik secara aman
    total_clicks = sum([(l.get("clicks") or 0) for l in links]) + sum([(p.get("clicks") or 0) for p in pastes])

    # Ambil yang terbaru
    links_sorted = sorted(links, key=lambda x: x.get("created_at") or "", reverse=True)[:5]
    pastes_sorted = sorted(pastes, key=lambda x: x.get("created_at") or "", reverse=True)[:5]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,  # pakai email saja
        "total_links": len(links),
        "total_pastes": len(pastes),
        "total_clicks": total_clicks,
        "recent_links": links_sorted,
        "recent_pastes": pastes_sorted
    })
