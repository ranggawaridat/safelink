from datetime import datetime
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from config import supabase
from services.utils import random_code
from services.core import templates

router = APIRouter(prefix="/shortlink", tags=["shortlink"])

@router.get("/", response_class=HTMLResponse)
def shortlink_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    try:
        user = supabase.auth.get_user(token).user
    except Exception:
        return RedirectResponse("/login")

    # Ambil semua shortlink milik user
    links = (
        supabase.table("links")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
        .data or []
    )

    # Ambil kode shortlink baru (jika baru dibuat)
    new_code = request.query_params.get("new")
    new_link = None
    if new_code:
        
        # scheme = "https" if request.url.hostname == "safelinku.site" else request.url.scheme
        # base_url = f"{scheme}://{request.url.hostname}"
        # new_link = {
        #     "full_url": f"{base_url}/s/{new_code}",
        #     "short_code": new_code
        # }

        new_link = {
            "full_url": f"https://{request.url.hostname}/s/{new_code}",
            "short_code": new_code
        }


    return templates.TemplateResponse("shortlink.html", {
        "request": request,
        "user": user,
        "links": links,
        "new_link": new_link
    })


@router.post("/", response_class=HTMLResponse)
def create_shortlink(request: Request, url: str = Form(...)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    try:
        user = supabase.auth.get_user(token).user
    except Exception:
        return RedirectResponse("/login")

    # Bersihkan & validasi URL
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Cegah input URL kosong atau tidak valid
    if "." not in url:
        return HTMLResponse("<h3>URL tidak valid.</h3>", status_code=400)

    # Generate short code unik
    while True:
        short_code = random_code()
        existing = (
            supabase.table("links")
            .select("id")
            .eq("short_code", short_code)
            .execute()
        )
        if not existing.data:
            break

    # Simpan data shortlink baru
    supabase.table("links").insert({
        "user_id": user.id,
        "original_url": url,
        "short_code": short_code,
        "clicks": 0,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    # Redirect dengan pesan sukses
    return RedirectResponse(f"/shortlink?new={short_code}", status_code=303)


@router.get("/s/{short_code}")
def redirect_shortlink(short_code: str):
    # Cari data link berdasarkan short_code
    response = (
        supabase.table("links")
        .select("*")
        .eq("short_code", short_code)
        .execute()
    )
    data = response.data

    if not data:
        return HTMLResponse("<h3>Shortlink tidak ditemukan.</h3>", status_code=404)

    link = data[0]

    # Tambahkan klik +1
    new_clicks = (link.get("clicks") or 0) + 1
    supabase.table("links").update({"clicks": new_clicks}).eq("id", link["id"]).execute()

    # Redirect ke original_url
    return RedirectResponse(link["original_url"])