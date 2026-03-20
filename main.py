import os
from pathlib import Path
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

BASE_DIR = Path(__file__).parent

app = get_fast_api_app(
    agents_dir=str(BASE_DIR),
    session_service_uri=None,
    allow_origins=["*"],
    web=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(content="<h1>index.html not found</h1>", status_code=404)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
