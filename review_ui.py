from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

app = FastAPI(title="MCP Review UI", version="1.0")
templates = Jinja2Templates(directory="templates")

API_URL = "http://api:8080/api"

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/changes")
            response.raise_for_status()
            logs = response.json()
        except httpx.RequestError as e:
            print(f"Error fetching changes from API: {e}")
            logs = []
    return templates.TemplateResponse("index.html", {"request": request, "logs": logs})