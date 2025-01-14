from loguru import logger
from api_utils import loguru_helper as log

if __name__ == "__main__":
    print("Starting logs")

    # Enable or disable debug logging
    DEBUG_LOGGING = False

    if DEBUG_LOGGING:
        log.setup_logger(logger, config=False)
    else:
        log.setup_logger(logger, config=True)

    print("Initializing")

try:
    import os
    import sys

    import uvicorn
    from fastapi import (
        APIRouter,
        Depends,
        FastAPI,
        HTTPException,
        Query,
        Request,
    )
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    from fastapi_utils.cbv import cbv

    print("Initializing TTS Engines")
    from realtimetts_helper import TTSBuilder

except ImportError as e:
    logger.warning(f"Module(s) {e} is not installed")
    print("exiting")
    sys.exit(1)

app = FastAPI()
router = APIRouter()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Middleware to add Content Security Policy headers to each response.

    Args:
        request (Request): The incoming HTTP request.
        call_next (Callable): The next request handler.

    Returns:
        Response: The modified response with added security headers.
    """
    csp = {
        "default-src": "'self'",
        "script-src": "'self'",
        "style-src": "'self' 'unsafe-inline'",
        "img-src": "'self' data:",
        "font-src": "'self' data:",
        "media-src": "'self' blob:",
    }
    csp_string = "; ".join(f"{key} {value}" for key, value in csp.items())
    # Forward the request to the next middleware or endpoint
    response = await call_next(request)
    # Adding the Content-Security-Policy header
    response.headers["Content-Security-Policy"] = csp_string
    return response

tts_server_instance = TTSProcessor()

def _get_tts_server() -> TTSProcessor:
    return tts_server_instance

@cbv(router)
class TTSApi:

    tts_server: TTSProcessor = Depends(_get_tts_server)

    @router.get("/set_engine")
    def set_engine(self, request: Request, engine_name: str = Query(...)):
        if engine_name not in self.engines:
            return {"error": "Engine not supported"}
        try:
            self._set_engine(engine_name)
            return {"message": f"Switched to {engine_name} engine"}
        except Exception as e:
            logger.error(f"Error switching engine: {str(e)}")
            return {"error": "Failed to switch engine"}

    @router.get("/tts")
    async def tts(self, request: Request, text: str = Query(...)):
        generator = self.tts_server.tts_stream(request, text)
        return StreamingResponse(generator, media_type="audio/wav")

    @router.get("/get_engines")
    def get_engines(self):
        return list(self.tts_server.engines.keys())

    @router.get("/get_voices")
    def get_voices(self):
        voices_list = []
        for voice in self.tts_server.voices[
            self.tts_server.current_engine.engine_name
        ]:
            voices_list.append(voice.name)
        return voices_list

    @router.get("/set_voices")
    def set_voice(self, request: Request, voice_name: str = Query(...)):
        print(f"Getting request: {voice_name}")
        if not self.tts_server.current_engine:
            print("No engine is currently selected")
            return {"error": "No engine is currently selected"}

        try:
            print(f"Setting voice to {voice_name}")
            self.tts_server.current_engine.set_voice(voice_name)
            return {"message": f"Voice set to {voice_name} successfully"}
        except Exception as e:
            print(f"Error setting voice: {str(e)}")
            logger.error(f"Error setting voice: {str(e)}")
            return {"error": "Failed to set voice"}

app.include_router(router)

if __name__ == "__main__":
    PORT = int(os.environ.get("TTS_FASTAPI_PORT", 8000))

    print("Server ready")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
