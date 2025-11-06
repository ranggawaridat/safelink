from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from config import supabase
import os
from services.core import templates, get_user, is_admin

is_dev = os.getenv("ENV", "dev") == "dev"

router = APIRouter(tags=["auth"])

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    msg = request.query_params.get("msg")

    # cek apakah sudah login
    token = request.cookies.get("access_token")
    if token:
        try:
            # verifikasi token untuk memastikan masih valid
            supabase.auth.get_user(token)
            return RedirectResponse(url="/dashboard", status_code=302)
        except Exception:
            pass  # kalau token invalid, biarkan lanjut ke halaman login

    return templates.TemplateResponse("login.html", {"request": request, "msg": msg})


@router.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        auth = supabase.auth.sign_in_with_password({"email": email, "password": password})
        session = auth.session

         # 🪄 arahkan ke dashboard dan simpan access_token di cookie
        response = RedirectResponse("/dashboard", status_code=302)
        response.set_cookie(
            key="access_token",
            value=session.access_token,
            httponly=True,
            max_age=60 * 60 * 24 * 7,  # 7 hari
            secure=not is_dev, # aktif hanya di HTTPS (production)
            samesite="lax"
        )
        return response
    except Exception as e:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Email atau password salah"})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
async def register_post(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        user = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })

        # kirim pesan sukses via query parameter
        response = RedirectResponse(url="/login?msg=success", status_code=302)
        return response
    except Exception as e:
        return templates.TemplateResponse("register.html", {"request": request, "error": str(e)})


@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    # hapus cookie access_token
    response.delete_cookie("access_token")
    return response
