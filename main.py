from fastapi import FastAPI, Request, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from routes import auth, dashboard, links, admin

app = FastAPI()

# Configuration
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Include Routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(links.router)
app.include_router(admin.router)










