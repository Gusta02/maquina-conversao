import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.voice_engine import VoiceEngine
from dotenv import load_dotenv

# 1. Carregar variáveis de ambiente
load_dotenv()

# 2. Setup de Logging Estruturado (Salva no arquivo para operação noturna)
log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "app.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("app_logger")

# 3. Setup da API FastAPI
app = FastAPI(title="Máquina de Conversão - API", version="1.0.0")
voice_engine = VoiceEngine()

# 4. Modelos de Validação (Payload)
class VideoRequest(BaseModel):
    title: str
    text_content: str
    lang: str = "EN-US"

# 5. Rotas
@app.get("/")
def health_check():
    return {"status": "ok", "message": "API Operacional"}

@app.post("/v1/video/generate")
async def generate_video(payload: VideoRequest):
    logger.info(f"Recebida requisição para gerar vídeo: {payload.title}")

    # Etapa 1 da Pipeline: Gerar a régua de tempo (Áudio)
    audio_result = await voice_engine.generate(
        text=payload.text_content, 
        lang=payload.lang
    )
    
    if audio_result["status"] == "error":
        logger.error("Falha na geração do áudio. Abortando pipeline.")
        raise HTTPException(status_code=500, detail=audio_result["message"])

    # TODO nas próximas Sprints: Integrar mineração de vídeo e renderização aqui.

    return {
        "status": "success",
        "step": "audio_generated",
        "data": audio_result
    }