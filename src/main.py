import os
import logging
import shutil
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from dotenv import load_dotenv

from src.voice_engine import VoiceEngine
from src.llm_engine import LLMEngine
from src.project_manager import ProjectManager
from src.media_miner import MediaMiner
from src.video_engine import VideoEngine

# 1. Carregar Variáveis de Ambiente
load_dotenv()

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

# --- ROTA 2: MOTOR DE RENDERIZAÇÃO (VOZ + VÍDEO) ---
@app.post("/v1/video/render")
async def render_video(payload: RenderRequest):
    logger.info(f"=== Iniciando Renderização: {payload.theme} ===")
    
    paths = project_manager.create_project_structure(payload.theme)
    processed_scenes = []

    for scene in payload.scenes:
        # 1. Gerar Áudio (Régua de tempo)
        audio_result = await voice_engine.generate_to_path(
            text=scene.get('narration'), 
            lang=payload.lang,
            target_dir=paths["audio"],
            scene_id=scene.get('id')
        )
        
        # 2. Baixar Vídeo (Mídia bruta)
        video_result = media_miner.download_video(
            query=scene.get('search_query'),
            target_dir=paths["video"],
            scene_id=scene.get('id')
        )
        
        # Guardar os caminhos para o montador
        scene['audio_file'] = audio_result['file_path']
        scene['duration'] = audio_result['duration_seconds']
        scene['video_file'] = video_result.get('file_path')
        processed_scenes.append(scene)

    # 3. CHAMADA DO MOTOR DE VÍDEO (A Montagem Real)
    # Aqui o sistema junta as peças e gera o arquivo FINAL.mp4
    render_result = video_engine.render_timeline(
        processed_scenes=processed_scenes,
        output_dir=paths["root"],
        theme_slug=payload.theme
    )

    if render_result["status"] == "error":
        raise HTTPException(status_code=500, detail=render_result["message"])

    # 4. Cleanup opcional (Deleta os brutos se solicitado)
    if payload.cleanup:
        try:
            # Agora deletamos tanto audio quanto video brutos, mantendo só o FINAL.mp4
            import shutil
            shutil.rmtree(paths["audio"])
            shutil.rmtree(paths["video"])
            logger.info(f"Cleanup completo para o projeto: {payload.theme}")
        except Exception as e:
            logger.warning(f"Falha no cleanup: {e}")

    return {
        "status": "success",
        "message": "Vídeo renderizado com sucesso!",
        "video_path": render_result["file_path"]
    }