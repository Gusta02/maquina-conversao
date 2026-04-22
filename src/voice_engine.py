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

    async def generate(self, text: str, lang: str = "EN-US") -> dict:
        """
        Gera o áudio, salva localmente e retorna o caminho e a duração exata.
        """
        voice_id = self.voices.get(lang.upper(), self.voices["EN-US"])
        file_id = str(uuid.uuid4())
        output_path = os.path.join(self.tmp_dir, f"{file_id}.mp3")

        try:
            logger.info(f"Iniciando geração de voz ({lang}) - ID: {file_id}")
            
            # Geração do áudio via edge-tts
            communicate = edge_tts.Communicate(text, voice_id)
            await communicate.save(output_path)
            
            # Extração da régua de tempo (Duração)
            audio_meta = MP3(output_path)
            duration_seconds = audio_meta.info.length
            
            logger.info(f"Áudio gerado com sucesso. Duração: {duration_seconds:.2f}s")
            
            return {
                "status": "success",
                "file_id": file_id,
                "file_path": output_path,
                "duration_seconds": duration_seconds,
                "voice_used": voice_id
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar locução: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }