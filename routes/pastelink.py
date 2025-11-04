from datetime import datetime
import re
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from config import supabase
from services.utils import random_code

router = APIRouter(prefix="/pastelink", tags=["pastelink"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def pastelink_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    try:
        user = supabase.auth.get_user(token).user
    except Exception:
        return RedirectResponse("/login")

    pastes = supabase.table("pastes").select("*").eq("user_id", user.id).execute().data

    return templates.TemplateResponse("pastelink.html", {
        "request": request,
        "user": user,
        "pastes": pastes
    })


@router.post("/", response_class=HTMLResponse)
def create_paste(request: Request, content: str = Form(...)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    try:
        user = supabase.auth.get_user(token).user
    except Exception:
        return RedirectResponse("/login")

    # generate short code unik
    while True:
        short_code = random_code()
        existing = supabase.table("pastes").select("id").eq("short_code", short_code).execute()
        if not existing.data:
            break

    # simpan paste baru
    supabase.table("pastes").insert({
        "user_id": user.id,
        "content": content,
        "short_code": short_code,
        "clicks": 0,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    return RedirectResponse("/pastelink", status_code=303)


@router.get("/p/{code}", response_class=HTMLResponse)
async def redirect_paste(request: Request, code: str):
    res = supabase.table("pastes").select("*").eq("short_code", code).execute()
    data = res.data

    if not data:
        return HTMLResponse("<h3>Paste tidak ditemukan.</h3>", status_code=404)

    paste = data[0]

    # tambah klik +1
    new_clicks = (paste.get("clicks") or 0) + 1
    supabase.table("pastes").update({"clicks": new_clicks}).eq("id", paste["id"]).execute()

    # ubah link jadi clickable
    def linkify(text: str) -> str:
        pattern = r'(https?://[^\s]+)'
        return re.sub(pattern, r'<a href="\1" target="_blank">\1</a>', text)

    linked_content = linkify(paste["content"])

    return templates.TemplateResponse("paste_view.html", {
        "request": request,
        "content": linked_content,
        "short_code": code
    })
