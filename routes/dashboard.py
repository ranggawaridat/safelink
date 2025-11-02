from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from services.user_service import get_user_profile
from config import supabase

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard", response_class=HTMLResponse)
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
