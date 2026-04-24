import os
import logging
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, CompositeAudioClip, afx
from proglog import ProgressBarLogger

logger = logging.getLogger("app_logger")

class CancelableLogger(ProgressBarLogger):
    def __init__(self, cancel_callback):
        super().__init__()
        self.cancel_callback = cancel_callback

    def callback(self, **kw):
        # A cada frame renderizado, ele pergunta: "O chefe mandou parar?"
        if self.cancel_callback and self.cancel_callback():
            raise Exception("CANCELADO_PELO_USUARIO")

class VideoEngine:
    def __init__(self):
        self.target_resolution = (1920, 1080)
        # Caminho para a música de fundo
        self.bg_music_path = r"C:\Users\Gustavo\Desktop\Gustavo\projetos_facul\MaquinadeConversao\assets\bg_music.mp3"

    def _prepare_clip(self, video_path: str, audio_path: str, duration: float, narration_text: str):
        """
        Prepara a cena com: Corte, Áudio, Redimensionamento e Legenda Central.
        """
        try:
            video_clip = VideoFileClip(video_path).subclipped(0, duration)
            audio_clip = AudioFileClip(audio_path)
            
            # Sincronia Base
            synced_clip = video_clip.with_audio(audio_clip)
            synced_clip = synced_clip.resized(self.target_resolution)

            # --- O POLIMENTO: LEGENDA ANIMADA ---
            # Cria o clipe de texto (Sintaxe MoviePy v2)
            # Dica: 'stroke_color' e 'stroke_width' criam aquela borda preta grossa, essencial para leitura
            txt_clip = TextClip(
                font="C:/Windows/Fonts/arialbd.ttf", 
                text=f"{narration_text}\n ",
                font_size=40, 
                color="white",
                stroke_color="black",
                stroke_width=2,
                method="caption", # Permite quebra de linha automática
                size=(1300, None) # Limita a largura do texto na tela
            ).with_duration(duration)

            # Posiciona o texto no centro da tela (você pode usar ('center', 'bottom') também)
            txt_clip = txt_clip.with_position(("center", 920))

            # Sobrepõe o texto no vídeo (CompositeVideoClip)
            final_scene = CompositeVideoClip([synced_clip, txt_clip])

            return final_scene
            
        except Exception as e:
            logger.error(f"Erro ao preparar clipe com legenda {video_path}: {e}")
            return None

    def render_timeline(self, processed_scenes: list, output_dir: str, theme_slug: str, cancel_check=None) -> dict:
        logger.info("Iniciando a montagem da Timeline com Legendas...")
        clips_to_join = []
        
        for scene in processed_scenes:
            if not scene.get('video_file') or not scene.get('audio_file'):
                continue
                
            # Note que agora passamos o 'narration_text' para o método
            clip = self._prepare_clip(
                video_path=scene['video_file'],
                audio_path=scene['audio_file'],
                duration=scene['duration'],
                narration_text=scene.get('narration')
            )
            
            if clip:
                clips_to_join.append(clip)

        if not clips_to_join:
            return {"status": "error", "message": "Nenhum clipe válido para renderizar."}

        # Concatena os clipes de vídeo com legendas
        final_video = concatenate_videoclips(clips_to_join, method="compose")
        
        # --- O POLIMENTO: MÚSICA DE FUNDO ---
        if os.path.exists(self.bg_music_path):
            try:
                logger.info("Aplicando trilha sonora de fundo...")
                bg_music = AudioFileClip(self.bg_music_path)
                
                # Faz um loop da música caso ela seja menor que o vídeo, e depois corta no tamanho exato do vídeo
                # O parâmetro do loop no v2 costuma ser bg_music.fx(vfx.loop, duration=final_video.duration) 
                # Mas para garantir, vamos cortar direto se a música for grande o suficiente.
                bg_music = bg_music.subclipped(0, final_video.duration)
                
                # Abaixa o volume da música radicalmente (-20dB ou ~0.15) para não brigar com a narração
                bg_music = bg_music.with_effects([afx.MultiplyVolume(0.15)])
                
                # Mixa o áudio das cenas (Voz) com o áudio da música
                final_audio = CompositeAudioClip([final_video.audio, bg_music])
                final_video = final_video.with_audio(final_audio)
            except Exception as e:
                logger.warning(f"Não foi possível aplicar a música de fundo: {e}")
        else:
            logger.warning(f"Música de fundo não encontrada em {self.bg_music_path}. Renderizando sem trilha.")

        output_file = os.path.join(output_dir, f"{theme_slug}_FINAL.mp4")
        logger.info(f"Iniciando renderização de {output_file}...")

        # Instancia o nosso logger espião
        spy_logger = CancelableLogger(cancel_check) if cancel_check else None

        try:
            final_video.write_videofile(
                output_file,
                fps=30,
                codec="libx264", 
                audio_codec="aac",
                preset="ultrafast",
                threads=4,
                logger=spy_logger # <-- Injeta ele aqui (substitua o logger=None)
            )

            # OPÇÃO 2: MODO PRODUÇÃO (Sua máquina Ryzen 7 + RX 7650 XT)
            # Quando voltar pro seu PC principal, comente o bloco acima e descomente este bloco abaixo.
            # final_video.write_videofile(
            #     output_file,
            #     fps=30,
            #     codec="h264_amf",   # <--- A mágica da aceleração da placa AMD!
            #     audio_codec="aac",
            #     preset="fast",
            #     logger=spy_logger
            # )
            
            # =====================================================================

            final_video.close()
            for c in clips_to_join:
                c.close()

            return {"status": "success", "file_path": output_file}

        except Exception as e:
            # Captura a nossa explosão controlada
            if str(e) == "CANCELADO_PELO_USUARIO":
                logger.warning("Renderização abortada com sucesso pelo usuário.")
                return {"status": "error", "message": "🛑 Operação abortada."}
                
            logger.error(f"Erro fatal: {e}")
            return {"status": "error", "message": str(e)}