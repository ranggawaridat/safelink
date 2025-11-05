from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from config import supabase
from io import StringIO
import csv

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login")

    try:
        user = supabase.auth.get_user(token).user
    except Exception:
        return RedirectResponse("/login", status_code=302)

    profile_query = supabase.table("user_profiles").select("*").eq("id", user.id).execute()
    if not profile_query.data:
        return HTMLResponse("<h3>Profile not found</h3>", status_code=404)

    profile = profile_query.data[0]
    if profile["role"] != "admin":
        return HTMLResponse("<h3>Unauthorized</h3>", status_code=403)


    # Ambil semua data
    users = supabase.table("user_profiles").select("id, email, role").execute().data or []
    links = supabase.table("links").select("id, user_id, clicks, created_at").execute().data or []
    pastes = supabase.table("pastes").select("id, user_id, clicks, created_at").execute().data or []

    # Pastikan semua data valid (hindari NoneType)
    for lst in (links, pastes):
        for item in lst:
            if item.get("clicks") is None:
                item["clicks"] = 0
            if not item.get("user_id"):
                item["user_id"] = "unknown"

    # --- STATISTIK UMUM ---
    stats = {
        "total_users": len(users),
        "total_links": len(links),
        "total_pastes": len(pastes),
        "total_clicks_links": sum(int(l.get("clicks", 0) or 0) for l in links),
        "total_clicks_pastes": sum(int(p.get("clicks", 0) or 0) for p in pastes),
    }

    # Tambahkan statistik turunan
    stats["total_clicks_all"] = stats["total_clicks_links"] + stats["total_clicks_pastes"]
    stats["avg_clicks_per_link"] = (
        round(stats["total_clicks_links"] / stats["total_links"], 2)
        if stats["total_links"] > 0 else 0
    )
    stats["avg_clicks_per_paste"] = (
        round(stats["total_clicks_pastes"] / stats["total_pastes"], 2)
        if stats["total_pastes"] > 0 else 0
    )

    # --- STATISTIK PER USER ---
    user_lookup = {u["id"]: u for u in users}
    user_stats = []

    for u in users:
        u_id = u["id"]
        user_links = [l for l in links if l["user_id"] == u_id]
        user_pastes = [p for p in pastes if p["user_id"] == u_id]
        user_stat = {
            "email": u["email"],
            "role": u.get("role", "user"),
            "link_count": len(user_links),
            "paste_count": len(user_pastes),
            "total_clicks_links": sum(l["clicks"] for l in user_links),
            "total_clicks_pastes": sum(p["clicks"] for p in user_pastes),
        }
        user_stat["total_clicks"] = (
            user_stat["total_clicks_links"] + user_stat["total_clicks_pastes"]
        )
        user_stats.append(user_stat)

    # --- DATA TERBARU (hindari error kalau created_at kosong) ---
    def sort_by_created(data):
        return sorted(data, key=lambda x: x.get("created_at") or "", reverse=True)

    latest_links = sort_by_created(links)[:10]
    latest_pastes = sort_by_created(pastes)[:10]

    confirm = request.query_params.get("confirm")

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "users": user_stats,
        "latest_links": latest_links,
        "latest_pastes": latest_pastes,
        "confirm": confirm,
    })


# --- EXPORT BACKUP CSV ---
@router.get("/export/{datatype}")
def export_backup(datatype: str, request: Request):
    if datatype not in ["links", "pastes"]:
        return HTMLResponse("<h3>Invalid data type</h3>", status_code=400)

    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)

    try:
        user = supabase.auth.get_user(token).user
    except Exception:
        return RedirectResponse("/login", status_code=302)

    profile_query = supabase.table("user_profiles").select("*").eq("id", user.id).execute()
    if not profile_query.data or profile_query.data[0]["role"] != "admin":
        return HTMLResponse("<h3>Unauthorized</h3>", status_code=403)

    data = supabase.table(datatype).select("*").execute().data
    if not data:
        return HTMLResponse("<h3>No data to export</h3>", status_code=404)

    # Generate CSV in memory
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

    output.seek(0)
    headers = {
        "Content-Disposition": f"attachment; filename={datatype}_backup.csv"
    }

    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)