from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from config import supabase
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["auth"])

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        auth = supabase.auth.sign_in_with_password({"email": email, "password": password})
        session = auth.session
        response = RedirectResponse("/dashboard", status_code=302)
        response.set_cookie(key="access_token", value=session.access_token, httponly=True)
        return response
    except Exception as e:
        return templates.TemplateResponse("login.html", {"request": request, "error": str(e)})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
async def register_post(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        # create user via Supabase Auth (service role key)
        user = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True  # Set to True if you want to auto-confirm the email
        })

        return RedirectResponse("/login", status_code=302)
    except Exception as e:
        return templates.TemplateResponse("register.html", {"request": request, "error": str(e)})

@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    # hapus cookie access_token
    response.delete_cookie("access_token")
    return response
