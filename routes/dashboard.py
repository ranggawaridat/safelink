from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from services.user_service import get_user_profile
from config import supabase
from typing import Optional

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, paste: str | None = None):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    try:
        user = supabase.auth.get_user(token).user
    except Exception:
        return RedirectResponse("/login")

    profile = get_user_profile(user.id)
    if not profile:
        return HTMLResponse("<h3>Profile not found</h3>")
    
    paste_link = None
    if paste:
        paste_link = f"https://{request.url.hostname}/p/{paste}"

    # ambil link milik user
    links = supabase.table("links").select("*").eq("user_id", user.id).execute().data
    pastes = supabase.table("pastes").select("*").eq("user_id", user.id).execute().data

    total_clicks = sum(l["clicks"] for l in links)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "profile": profile,
        "links": links,
        "paste_link": paste_link,
        "pastes": pastes,
        "total_clicks": total_clicks,
        "total_links": len(links)
    })
