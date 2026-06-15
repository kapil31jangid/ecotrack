import sys
import os
import time
import uuid
import asyncio
import logging
import traceback
from contextlib import asynccontextmanager

# Add path helper to support running from root or from within backend folder
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.config import APP_VERSION, GOOGLE_CLOUD_PROJECT
from backend.models import (
    FootprintInput,
    FootprintResult,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    CategoryBreakdown,
    Tip,
)
from backend.calculator import calculate_total_footprint
from backend.ai_service import get_ai_response, get_ai_tips, get_ai_insights
from backend.firestore_service import (
    save_footprint,
    get_footprint_history,
    save_chat_message,
    aggregate_weekly_stats,
)
from backend.logging_service import setup_logging, setup_tracing, get_tracer

# 100% Google AI provider declaration
AI_PROVIDER = "Google Gemini AI (REST API)"

# Rate Limiter setup
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup hook
    global logger
    logger = setup_logging()
    setup_tracing()
    logger.info(f"EcoTrack started. AI provider: {AI_PROVIDER}")
    yield
    # Shutdown hook
    logger.info("EcoTrack application shutting down.")

app = FastAPI(
    title="EcoTrack API",
    version=APP_VERSION,
    lifespan=lifespan,
)

# Mount static frontend files if the dist folder exists (production container)
_frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="assets")

# Configure Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# 1. X-Request-ID and Request Timing Logger Middleware
@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    start_time = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        tb_str = traceback.format_exc()
        logging.getLogger("ecotrack").error(
            f"HTTP Exception: {request.method} {request.url.path} failed. "
            f"Duration: {duration_ms}ms. Request ID: {request_id}\n{tb_str}"
        )
        return JSONResponse(
            status_code=500,
            content={"error": "An internal server error occurred.", "request_id": request_id},
        )
    
    duration_ms = int((time.time() - start_time) * 1000)
    logging.getLogger("ecotrack").info(
        f"Request: {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration_ms}ms - Request ID: {request_id}"
    )
    response.headers["X-Request-ID"] = request_id
    return response

# 3. Global exception handlers to protect stack traces
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "request_id": request_id}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=422,
        content={"error": "Validation failed", "detail": exc.errors(), "request_id": request_id}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logging.getLogger("ecotrack").error(f"Unhandled error for Request {request_id}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An internal server error occurred.", "request_id": request_id}
    )

# Endpoints
@app.get("/api/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Endpoint indicating API health state."""
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        ai_provider=AI_PROVIDER
    )

@app.post("/api/calculate", response_model=FootprintResult)
async def calculate_footprint_endpoint(input_data: FootprintInput) -> FootprintResult:
    """
    Validate FootprintInput, calculate emissions, 
    and save log to Firestore asynchronously.
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("calculate_footprint"):
        # Run calculation
        result_dict = calculate_total_footprint(input_data.model_dump())
        
        # Override tips with Gemini AI tips if possible
        try:
            ai_tips = await get_ai_tips(input_data.model_dump(), result_dict["category_breakdown"])
            result_dict["tips"] = ai_tips
            logging.getLogger("ecotrack").info(f"Successfully generated Gemini AI tips for session: {input_data.session_id}")
        except Exception as e:
            logging.getLogger("ecotrack").warning(
                f"Failed to generate Gemini AI tips for session {input_data.session_id}: {str(e)}. "
                f"Falling back to local rule-based tips."
            )
        
        # Generate dashboard insights with Gemini AI if possible
        try:
            ai_insights = await get_ai_insights(input_data.model_dump(), result_dict["category_breakdown"])
            result_dict["insights"] = ai_insights
            logging.getLogger("ecotrack").info(f"Successfully generated Gemini AI insights for session: {input_data.session_id}")
        except Exception as e:
            logging.getLogger("ecotrack").warning(
                f"Failed to generate Gemini AI insights for session {input_data.session_id}: {str(e)}. "
                f"Falling back to default insights."
            )
            # Default deterministic fallback insight
            highest_category = max(result_dict["category_breakdown"], key=result_dict["category_breakdown"].get)
            result_dict["insights"] = (
                f"Based on your breakdown, your highest monthly emissions come from the {highest_category} category. "
                "Focus on the customized action steps below to start making a positive impact today."
            )
        
        # Add session and timestamp to response
        result_dict["session_id"] = input_data.session_id
        result_dict["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        # Fire-and-forget save operation to Firestore
        asyncio.create_task(
            save_footprint(input_data.session_id, input_data.model_dump(), result_dict)
        )
        
        return FootprintResult(**result_dict)

@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat_endpoint(request: Request, chat_req: ChatRequest) -> ChatResponse:
    """
    Send a message to Vertex AI Gemini incorporating carbon footprint context.
    Rate-limited to 10 requests per minute per IP.
    """
    start_time = time.time()
    
    # Query Gemini response
    reply, model_used = await get_ai_response(
        chat_req.message, chat_req.footprint_context, chat_req.session_id
    )
    
    # Fire-and-forget save of user and AI response to chat history
    asyncio.create_task(
        save_chat_message(chat_req.session_id, "user", chat_req.message, "")
    )
    asyncio.create_task(
        save_chat_message(chat_req.session_id, "model", reply, model_used)
    )
    
    duration_ms = int((time.time() - start_time) * 1000)
    logging.getLogger("ecotrack").info(
        f"Chat Completed: session={chat_req.session_id}, model={model_used}, duration={duration_ms}ms"
    )
    
    return ChatResponse(
        reply=reply,
        session_id=chat_req.session_id,
        model_used=model_used
    )

@app.get("/api/history/{session_id}", response_model=list[FootprintResult])
async def history_endpoint(session_id: str) -> list[FootprintResult]:
    """Retrieve all calculations logged for a given session."""
    history = await get_footprint_history(session_id)
    # Map raw Firestore documents to FootprintResult model structure
    results = []
    for h in history:
        res = h.get("result", {})
        # Safety injection of session and timestamp if missing
        res["session_id"] = h.get("session_id", session_id)
        res["timestamp"] = h.get("timestamp", "")
        results.append(FootprintResult(**res))
    return results

@app.post("/api/admin/aggregate-stats")
async def aggregate_stats_endpoint(x_scheduler_job: str | None = Header(None, alias="X-CloudScheduler-JobName")) -> dict:
    """
    Run admin aggregation cron to compile analytics summary.
    Header validation checks for 'X-CloudScheduler-JobName'.
    """
    if not x_scheduler_job:
        raise HTTPException(
            status_code=403, detail="Forbid access: Missing scheduler invocation header"
        )
    
    stats = await aggregate_weekly_stats()
    return {"status": "ok", "stats": stats}

# ── Serve React frontend for all non-API routes ──────────────────────────────
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    """Serve the React SPA index.html for all non-API routes (client-side routing)."""
    index_file = os.path.join(_frontend_dist, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file, media_type="text/html")
    return JSONResponse(status_code=404, content={"error": "Frontend not found"})
