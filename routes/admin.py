from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from config import supabase

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    user = supabase.auth.get_user(token).user
    # pastikan hanya admin
    profile = supabase.table("user_profiles").select("*").eq("id", user.id).execute().data[0]
    if profile["role"] != "admin":
        return HTMLResponse("<h3>Unauthorized</h3>", status_code=403)

    users = supabase.table("user_profiles").select("*").execute().data
    links = supabase.table("links").select("*").execute().data
    pastes = supabase.table("pastes").select("*").execute().data

    # hitung statistik
    stats = {
        "total_users": len(users),
        "total_links": len(links),
        "total_pastes": len(pastes),
        "total_clicks": sum(l.get("clicks", 0) for l in links),
    }

    # tambahkan jumlah link/paste per user
    user_stats = []
    for u in users:
        link_count = len([l for l in links if l["user_id"] == u["id"]])
        paste_count = len([p for p in pastes if p["user_id"] == u["id"]])
        user_stats.append({
            "email": u["email"],
            "role": u.get("role", "user"),
            "link_count": link_count,
            "paste_count": paste_count
        })

    latest_links = sorted(links, key=lambda x: x.get("created_at", ""), reverse=True)[:10]
    latest_pastes = sorted(pastes, key=lambda x: x.get("created_at", ""), reverse=True)[:10]

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "users": user_stats,
        "latest_links": latest_links,
        "latest_pastes": latest_pastes
    })
