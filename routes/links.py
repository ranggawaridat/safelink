from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from config import supabase, EARNING_PER_CLICK
from services.utils import random_code

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["Links"])


@router.post("/shorten")
async def shorten(request: Request, url: str = Form(...)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    try:
        user = supabase.auth.get_user(token).user
    except Exception:
        return RedirectResponse("/login")
    
    code = random_code()
    supabase.table("links").insert({
        "user_id": user.user.id, 
        "original_url": url, 
        "short_code": code
        }).execute()
    
    return RedirectResponse("/dashboard", status_code=302)

@router.get("/s/{code}", response_class=HTMLResponse)
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

