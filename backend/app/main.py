"""FastAPI entrypoint.

Run locally:  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
(0.0.0.0 lets your phone on the same Wi-Fi reach it via your PC's LAN IP.)
"""
import os
import mimetypes

# On Windows, Python's mimetypes reads the registry, which often maps ".js" to a
# wrong type (e.g. text/plain). Browsers then REFUSE to run the app's ES module
# scripts (CSS still applies, so you see only the background). Force the correct
# types here so the built frontend works when served by the backend.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("image/svg+xml", ".svg")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .config import settings
from .database import Base, engine, SessionLocal
from .routers import auth_router, vocab_router, stats_router, writing_router, practice_router
from .seed_util import ensure_user, import_cards_from_csv
from .migrations import run_migrations

app = FastAPI(title="TOEFL/GRE Study — Vocab SRS", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(vocab_router.router)
app.include_router(stats_router.router)
app.include_router(writing_router.router)
app.include_router(practice_router.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    # Bring an existing DB up to the current schema (roles + per-user progress)
    # BEFORE any ORM access, since the ORM now expects the new columns.
    run_migrations(engine, settings.app_username)
    db = SessionLocal()
    try:
        ensure_user(db)
        # Import the version-controlled vocab deck on every startup. The import
        # is idempotent (skips words already in the DB, case-insensitive), so it
        # safely TOPS UP the deck after each deploy: add words to
        # seed/starter_words.csv, git push, restart, and the new ones appear on
        # the server without touching the (gitignored) database file.
        starter = os.path.join(os.path.dirname(__file__), "..", "..", "seed", "starter_words.csv")
        starter = os.path.abspath(starter)
        if os.path.exists(starter):
            n = import_cards_from_csv(db, starter)
            if n:
                print(f"[startup] imported {n} new cards from seed CSV")
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Optionally serve the built frontend (frontend/dist) as static files. ---
# In local dev you'll usually run Vite (npm run dev) on :5173 and hit the API
# directly. In the Docker image the frontend is built and copied to
# /app/frontend/dist, so the backend serves the whole app on a single port.
# We mount /assets for the hashed JS/CSS bundles, and add a catch-all route
# that returns index.html for any non-API path so client-side routing works.
_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))

if os.path.isdir(_DIST):
    _ASSETS = os.path.join(_DIST, "assets")
    if os.path.isdir(_ASSETS):
        app.mount("/assets", StaticFiles(directory=_ASSETS), name="assets")

    @app.get("/")
    def _serve_index():
        return FileResponse(os.path.join(_DIST, "index.html"))

    # SPA fallback: any path that isn't an /api route or a real static file
    # returns index.html so the frontend router can handle it.
    @app.get("/{full_path:path}")
    def _spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = os.path.join(_DIST, full_path)
        if os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_DIST, "index.html"))
else:
    print(f"[startup] frontend dist not found at {_DIST}; serving API only")
