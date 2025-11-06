from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from config import supabase
from services.core import templates, get_user, is_admin

router = APIRouter(tags=["Redirect Shortlink"])

@router.get("/s/{code}", response_class=HTMLResponse)
async def redirect_link(request: Request, code: str):
    res = supabase.table("links").select("*").eq("short_code", code).execute()
    
    if not res.data or len(res.data) == 0:
        return HTMLResponse("<h3>Link not found</h3>")

    link = res.data[0]  # ambil dict pertama

    new_clicks = link["clicks"] + 1

    supabase.table("links").update({
        "clicks": new_clicks
    }).eq("short_code", code).execute()

    return templates.TemplateResponse("ad.html", {
        "request": request,
        "original_url": link["original_url"]
    })