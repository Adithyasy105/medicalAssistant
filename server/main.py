from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from middlewares.exception_handlers import catch_exception_middleware
from routes.upload_pdfs import router as upload_router
from routes.ask_question import router as ask_router




from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app=FastAPI(title="Medical Assistant API",description="API for AI Medical Assistant Chatbot")

# CORS Setup - Read from env or default to localhost for security
origins = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://localhost").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# routers
app.include_router(upload_router)
app.include_router(ask_router)

# Serve static files from the client directory
# We'll create index.html and app.js inside medicalAssistant/client/
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "client")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

# middleware exception handlers
app.middleware("http")(catch_exception_middleware)