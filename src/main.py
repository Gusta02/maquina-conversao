import os
import json
import shutil
import logging
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from src.llm_engine import LLMEngine
from src.media_miner import MediaMiner
from src.voice_engine import VoiceEngine
from src.video_engine import VideoEngine
from src.project_manager import ProjectManager

# 1. Carregar Variáveis de Ambiente
load_dotenv()

# Bandeira global de cancelamento
CANCEL_REQUESTED = False

# 2. Configuração de Logs Estruturados
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

# 3. Inicialização da API e Instâncias
app = FastAPI(title="Máquina de Conversão - API", version="1.1.0")
voice_engine = VoiceEngine()
llm_engine = LLMEngine()
project_manager = ProjectManager()
media_miner = MediaMiner()
video_engine = VideoEngine()


# 4. Modelos de Payload (Pydantic)
class ScriptRequest(BaseModel):
    theme: str
    lang: str = "EN-US"

class RenderRequest(BaseModel):
    theme: str
    scenes: List[Dict[str, Any]]
    lang: str = "EN-US"
    cleanup: bool = False # <-- Gatilho para limpar o SSD

# 5. Rotas da API
@app.get("/")
def health_check():
    return {"status": "ok", "message": "API Operacional"}

# --- ROTA 1: CHECKPOINT DE VALIDAÇÃO (CÉREBRO) ---
@app.post("/v1/video/script")
async def generate_script(payload: ScriptRequest):
    logger.info(f"=== Nova Requisição de Roteiro: {payload.theme} ===")
    
    # 5.1 Gera o Roteiro via LLM
    script_result = llm_engine.generate_script(theme=payload.theme, lang=payload.lang)
    if script_result["status"] == "error":
        raise HTTPException(status_code=500, detail=script_result["message"])
    
    # 5.2 Cria a Estrutura de Pastas Segura
    paths = project_manager.create_project_structure(payload.theme)
    
    # 5.3 Salva o JSON na pasta do projeto
    project_manager.save_script(paths["script"], script_result["data"])
    logger.info(f"Roteiro salvo com sucesso em: {paths['script']}")
    
    return {
        "status": "success",
        "step": "script_generated_awaiting_approval",
        "project_path": paths["root"],
        "data": script_result["data"]
    }

# --- ROTA 2: Motor de busca de videos ---
@app.get("/v1/media/search")
async def search_media(query: str):
    candidates = media_miner.search_candidates(query)
    return {"status": "success", "candidates": candidates}

# --- ROTA 3: MOTOR DE RENDERIZAÇÃO (VOZ + VÍDEO) ---
@app.post("/v1/video/render")
async def render_video(payload: RenderRequest):
    global CANCEL_REQUESTED
    CANCEL_REQUESTED = False # Reseta a cada nova chamada

    def is_cancelled():
        return CANCEL_REQUESTED

    async def event_generator():
        yield json.dumps({"status": "info", "message": "📦 Iniciando processo..."}) + "\n"
        paths = project_manager.create_project_structure(payload.theme)
        processed_scenes = []

        for i, scene in enumerate(payload.scenes):
            # Trava de segurança 1: Checa antes de cada cena
            if is_cancelled():
                yield json.dumps({"status": "error", "message": "🛑 Cancelado antes de processar mídias."}) + "\n"
                return

            yield json.dumps({"status": "info", "message": f"🎙️ Gerando cena {i+1}..."}) + "\n"
            audio_result = await voice_engine.generate_to_path(scene.get('narration'), payload.lang, paths["audio"], scene.get('id'))

            selected_url = scene.get('selected_video_url')
            if selected_url:
                video_result = media_miner.download_by_url(selected_url, paths["video"], scene.get('id'))
            else:
                video_result = media_miner.download_video(scene.get('search_query'), paths["video"], scene.get('id'))

            scene['audio_file'] = audio_result['file_path']
            scene['duration'] = audio_result['duration_seconds']
            scene['video_file'] = video_result.get('file_path')
            processed_scenes.append(scene)

        # Trava de segurança 2: Checa antes de mandar pro FFmpeg
        if is_cancelled():
             yield json.dumps({"status": "error", "message": "🛑 Cancelado antes da montagem."}) + "\n"
             return

        yield json.dumps({"status": "info", "message": "🎬 Montando Timeline (Pode cancelar se quiser)..."}) + "\n"
        
        # Passa a função espiã para o motor de vídeo
        render_result = video_engine.render_timeline(processed_scenes, paths["root"], payload.theme, cancel_check=is_cancelled)

        if render_result["status"] == "error":
            yield json.dumps({"status": "error", "message": render_result["message"]}) + "\n"
            return

        if payload.cleanup:
            yield json.dumps({"status": "info", "message": "🧹 Limpando arquivos brutos temporários..."}) + "\n"
            try:
                import shutil
                shutil.rmtree(paths["audio"])
                shutil.rmtree(paths["video"])
            except Exception as e:
                pass

        yield json.dumps({"status": "success", "message": "✨ Vídeo renderizado com sucesso!", "video_path": render_result["file_path"]}) + "\n"

    # O FastAPI agora retorna o Stream em vez de um dicionário final
    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.post("/v1/video/cancel")
def cancel_render():
    global CANCEL_REQUESTED
    CANCEL_REQUESTED = True
    logger.info("🚨 SINAL DE CANCELAMENTO RECEBIDO!")
    return {"status": "success", "message": "Cancelamento ativado."}