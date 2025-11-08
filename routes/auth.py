from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from config import supabase
from services.core import templates, get_user, is_admin
import os

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
        user = supabase.auth.sign_up({
            "email": email,
            "password": password,
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


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

@router.post("/forgot-password")
async def forgot_password_post(request: Request, email: str = Form(...)):
    try:
        # kirim email reset password dari Supabase
        redirect_url = "http://localhost:8000/reset-password" if is_dev else "https://safelinku.site/reset-password"
        supabase.auth.reset_password_for_email(email)

        msg = "Kami telah mengirimkan tautan reset password ke email kamu"
        return templates.TemplateResponse("forgot_password.html", {"request": request, "msg": msg})
    except Exception as e:
        return templates.TemplateResponse("forgot_password.html", {"request": request, "error": str(e)})
    

@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, access_token: str = None):
    # kalau Supabase kirim #access_token=... (hash), ambilnya via frontend
    # di sini kita cuma tampilkan form
    return templates.TemplateResponse(
        "reset_password.html",
        {"request": request, "access_token": access_token, "msg": None, "error": None}
    )

@router.post("/reset-password", response_class=HTMLResponse)
async def reset_password_submit(
    request: Request,
    password: str = Form(...),
    access_token: str = Form(...)
):
    try:
        # pakai access_token dari Supabase link recovery
        supabase.auth.set_session(access_token, None)
        supabase.auth.update_user({"password": password})

        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "msg": "Password berhasil diubah 💕 Silakan login kembali.", "error": None, "access_token": None},
        )

    except Exception as e:
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "msg": None, "error": str(e), "access_token": access_token},
        )