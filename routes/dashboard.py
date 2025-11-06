from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from config import supabase
from services.core import templates, get_user, is_admin

router = APIRouter(tags=["Dashboard"])

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)

    try:
        user = supabase.auth.get_user(token).user
    except Exception:
        return RedirectResponse("/login", status_code=302)


    # Ambil role user (admin / user)
    profile_data = supabase.table("user_profiles").select("role").eq("id", user.id).execute()
    role = profile_data.data[0]["role"] if profile_data.data else "user"
    is_admin = role == "admin"


    # Ambil semua shortlink dan pastelink milik user
    links = (
        supabase.table("links")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
        .data or []
    )

    pastes = (
        supabase.table("pastes")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
        .data or []
    )


    # Hitung total klik secara aman
    total_clicks = sum([(l.get("clicks") or 0) for l in links]) + sum([(p.get("clicks") or 0) for p in pastes])

    # Ambil yang terbaru
    links_sorted = sorted(links, key=lambda x: x.get("created_at") or "", reverse=True)[:5]
    pastes_sorted = sorted(pastes, key=lambda x: x.get("created_at") or "", reverse=True)[:5]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "is_admin": is_admin,
        "total_links": len(links),
        "total_pastes": len(pastes),
        "total_clicks": sum((l.get("clicks") or 0) for l in links) + sum((p.get("clicks") or 0) for p in pastes),
        "recent_links": sorted(links, key=lambda x: x.get("created_at") or "", reverse=True)[:5],
        "recent_pastes": sorted(pastes, key=lambda x: x.get("created_at") or "", reverse=True)[:5],
    })
