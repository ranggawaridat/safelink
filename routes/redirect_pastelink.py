import re
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from config import supabase

router = APIRouter(tags=["Redirect Paste"])
templates = Jinja2Templates(directory="templates")


@router.get("/p/{code}", response_class=HTMLResponse)
async def redirect_paste(request: Request, code: str):
    """Tampilkan konten paste berdasarkan kode"""
    res = supabase.table("pastes").select("*").eq("short_code", code).execute()
    data = res.data

    if not data:
        return HTMLResponse("<h3>Paste tidak ditemukan.</h3>", status_code=404)

    paste = data[0]

    # Tambahkan klik +1
    new_clicks = (paste.get("clicks") or 0) + 1
    supabase.table("pastes").update({"clicks": new_clicks}).eq("id", paste["id"]).execute()

    # Linkify konten (otomatis ubah URL jadi clickable)
    def linkify(text: str) -> str:
        pattern = r'(https?://[^\s]+)'
        return re.sub(pattern, r'<a href="\1" target="_blank">\1</a>', text)

    linked_content = linkify(paste["content"])

    return templates.TemplateResponse("paste_view.html", {
        "request": request,
        "content": linked_content,
        "short_code": code
    })
