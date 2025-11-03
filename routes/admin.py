from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from services.user_service import get_user_profile
from config import supabase

router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory="templates")


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)

    try:
        user = supabase.auth.get_user(token).user
    except Exception as e:
        print("Auth error:", e)
        return RedirectResponse("/login", status_code=302)

    # cek role admin
    profile = get_user_profile(user.id)
    if not profile or profile.get("role") != "admin":
        return HTMLResponse("<h3>Access denied</h3>")

    # ambil semua user
    users = supabase.table("user_profiles").select("*").execute().data or []

    # ambil statistik global
    links = supabase.table("links").select("clicks").execute().data or []

    total_clicks = sum([l.get("clicks", 0) or 0 for l in links])
  
    stats = {
        "total_clicks": total_clicks,
    }

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "users": users,
        "stats": stats,
        "user": profile
    })

