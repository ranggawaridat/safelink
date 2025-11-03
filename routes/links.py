from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from config import supabase
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
    
    # generate slug unik
    while True:
        code = random_code()
        existing = supabase.table("links").select("id").eq("short_code", code).execute()
        if not existing.data:  # kalau belum ada di DB
            break

    # Simpan link baru
    supabase.table("links").insert({
        "user_id": user.id,
        "original_url": url,
        "short_code": code
    }).execute()

    # ambil semua link untuk ditampilkan lagi
    links = supabase.table("links").select("*").eq("user_id", user.id).execute().data

    short_url = f"https://{request.url.hostname}/s/{code}"

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "links": links,
        "short_url": short_url
    })

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


@router.post("/paste")
async def create_paste(request: Request, content: str = Form(...)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)

    try:
        user = supabase.auth.get_user(token).user
    except Exception:
        return RedirectResponse("/login", status_code=302)

    # generate kode unik
    code = random_code()
    existing = supabase.table("pastes").select("*").eq("short_code", code).execute()
    while existing.data:
        code = random_code()
        existing = supabase.table("pastes").select("*").eq("short_code", code).execute()

    supabase.table("pastes").insert({
        "user_id": user.id,
        "short_code": code,
        "content": content
    }).execute()

    return RedirectResponse(f"/dashboard?paste={code}", status_code=302)

@router.get("/p/{code}", response_class=HTMLResponse)
async def view_paste(request: Request, code: str):
    res = supabase.table("pastes").select("*").eq("short_code", code).single().execute()
    if not res.data:
        return HTMLResponse("<h3>Paste not found</h3>", status_code=404)

    paste = res.data

    # Update clicks
    new_clicks = (paste.get("clicks") or 0) + 1
    supabase.table("pastes").update({"clicks": new_clicks}).eq("short_code", code).execute()

    # Deteksi link di dalam konten (otomatis bikin <a href>)
    import re
    def linkify(text):
        pattern = r'(https?://[^\s]+)'
        return re.sub(pattern, r'<a href="\1" target="_blank">\1</a>', text)

    linked_content = linkify(paste["content"])

    return templates.TemplateResponse("paste_view.html", {
        "request": request,
        "content": linked_content
    })
