from fastapi.templating import Jinja2Templates
from fastapi import Request
from config import supabase

# Inisialisasi Jinja2 Templates (tempat file .html)
templates = Jinja2Templates(directory="templates")

# Ambil user dari session
def get_user(request: Request):
    user = request.session.get("user")
    return user

# Cek apakah user adalah admin
def is_admin(request: Request):
    user = get_user(request)
    if not user:
        return False

    # Ambil data profile dari Supabase
    profile = supabase.table("user_profiles").select("*").eq("user_id", user["id"]).execute()
    if not profile.data:
        return False

    return profile.data[0].get("role") == "admin"
