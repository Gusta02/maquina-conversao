import os
import uuid
import edge_tts
from mutagen.mp3 import MP3
import logging

logger = logging.getLogger("app_logger")

class VoiceEngine:
    def __init__(self):
        # Vozes de alta qualidade fixadas
        self.voices = {
            "PT-BR": "pt-BR-AntonioNeural", # Voz masculina firme
            "EN-US": "en-US-ChristopherNeural" # Voz masculina estilo documentário
        }
        self.tmp_dir = os.path.join(os.getcwd(), "tmp")
        os.makedirs(self.tmp_dir, exist_ok=True)

    async def generate_to_path(self, text: str, lang: str, target_dir: str, scene_id: int) -> dict:
        """
        Gera o áudio e salva em um diretório específico com numeração sequencial.
        """
        voice_id = self.voices.get(lang.upper(), self.voices["EN-US"])
        # Nomeia o arquivo claramente, ex: scene_1.mp3
        output_path = os.path.join(target_dir, f"scene_{scene_id}.mp3")

        try:
            communicate = edge_tts.Communicate(text, voice_id)
            await communicate.save(output_path)
            
            audio_meta = MP3(output_path)
            duration_seconds = audio_meta.info.length
            
            return {
                "status": "success",
                "file_path": output_path,
                "duration_seconds": duration_seconds,
                "voice_used": voice_id
            }
        except Exception as e:
            logger.error(f"Erro ao gerar locução da cena {scene_id}: {str(e)}")
            return {"status": "error", "message": str(e)}