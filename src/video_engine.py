import os
import logging
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

logger = logging.getLogger("app_logger")

class VideoEngine:
    def __init__(self):
        # A resolução padrão do nosso canal (1080p horizontal)
        self.target_resolution = (1920, 1080)

    def _prepare_clip(self, video_path: str, audio_path: str, duration: float):
        """
        Prepara uma única cena: corta o vídeo no tamanho exato do áudio e redimensiona.
        """
        try:
            video_clip = VideoFileClip(video_path)
            audio_clip = AudioFileClip(audio_path)

            # Sincronia: Corta o vídeo para ter o tempo exato da narração
            # Se o vídeo baixar for menor que o áudio, o loop seria necessário aqui (simplificado para o MVP)
            synced_clip = video_clip.subclipped(0, duration)
            
            # Anexa o áudio ao vídeo
            synced_clip = synced_clip.with_audio(audio_clip)

            # Força o tamanho padrão para evitar erros na concatenação final
            synced_clip = synced_clip.resized(self.target_resolution)

            return synced_clip
            
        except Exception as e:
            logger.error(f"Erro ao preparar clipe {video_path}: {e}")
            return None

    def render_timeline(self, processed_scenes: list, output_dir: str, theme_slug: str) -> dict:
        """
        Recebe a lista de cenas prontas, junta tudo e renderiza o arquivo final.
        """
        logger.info("Iniciando a montagem da Timeline principal...")
        clips_to_join = []
        
        for scene in processed_scenes:
            # Pula cenas que falharam no download do vídeo ou áudio
            if not scene.get('video_file') or not scene.get('audio_file'):
                logger.warning(f"Cena {scene.get('id')} ignorada por falta de mídia.")
                continue
                
            clip = self._prepare_clip(
                video_path=scene['video_file'],
                audio_path=scene['audio_file'],
                duration=scene['duration']
            )
            
            if clip:
                clips_to_join.append(clip)

        if not clips_to_join:
            return {"status": "error", "message": "Nenhum clipe válido para renderizar."}

        # Concatena todos os clipes na ordem
        final_video = concatenate_videoclips(clips_to_join, method="compose")
        
        output_file = os.path.join(output_dir, f"{theme_slug}_FINAL.mp4")
        logger.info(f"Iniciando renderização de {output_file}...")

        try:
            # =====================================================================
            # CHAVE DE RENDERIZAÇÃO: STAGING vs PRODUÇÃO
            # =====================================================================
            
            # OPÇÃO 1: MODO TESTE / STAGING (Usa CPU)
            # Use esta opção enquanto estiver nessa máquina alternativa sem a RX 7650 XT.
            # É mais lento, mas garante que a lógica de montagem funciona perfeitamente.
            final_video.write_videofile(
                output_file,
                fps=30,
                codec="libx264", 
                audio_codec="aac",
                preset="ultrafast", # Rápido para não travar seu teste
                threads=4,          # Usa múltiplos núcleos do seu processador atual
                logger=None         # Desativa a barra de progresso poluída do MoviePy no terminal
            )

            # OPÇÃO 2: MODO PRODUÇÃO (Sua máquina Ryzen 7 + RX 7650 XT)
            # Quando voltar pro seu PC principal, comente o bloco acima e descomente este bloco abaixo.
            # final_video.write_videofile(
            #     output_file,
            #     fps=30,
            #     codec="h264_amf",   # <--- A mágica da aceleração da placa AMD!
            #     audio_codec="aac",
            #     preset="fast",
            #     logger=None
            # )
            
            # =====================================================================

            # Fecha os arquivos da memória para permitir que o Garbage Collector (cleanup) os delete depois
            final_video.close()
            for c in clips_to_join:
                c.close()

            logger.info("Renderização concluída com sucesso!")
            return {"status": "success", "file_path": output_file}

        except Exception as e:
            logger.error(f"Erro fatal na renderização final: {e}")
            return {"status": "error", "message": str(e)}