import os
from fastapi import Request
from fastapi.responses import JSONResponse

# Thêm biến A2A_API_KEY vào .env hoặc mặc định là "super-secret-key"
A2A_API_KEY = os.getenv("A2A_API_KEY", "super-secret-key")

async def auth_middleware(request: Request, call_next):
    # Cho phép truy cập Agent Card (.well-known) mà không cần auth
    if request.url.path == "/.well-known/agent.json":
        return await call_next(request)
        
    # Cho phép tuỳ chọn gọi bằng HTTP Bearer
    auth_header = request.headers.get("Authorization")
    if not auth_header or auth_header != f"Bearer {A2A_API_KEY}":
        return JSONResponse(status_code=401, content={"detail": "Unauthorized A2A Endpoint"})
        
    return await call_next(request)

def apply_auth(app):
    """Gắn Middleware Auth vào FastAPI app."""
    app.middleware("http")(auth_middleware)
