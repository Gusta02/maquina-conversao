import os
import requests
import logging

logger = logging.getLogger("app_logger")

class MediaMiner:
    def __init__(self):
        self.api_key = os.environ.get("PEXELS_API_KEY")
        self.base_url = "https://api.pexels.com/videos/search"
        self.headers = {"Authorization": self.api_key}

    def download_video(self, query: str, target_dir: str, scene_id: int) -> dict:
        """
        Busca um vídeo no Pexels e faz o download para a pasta do projeto.
        """
        logger.info(f"Buscando vídeo para a Cena {scene_id} | Query: '{query}'")
        output_path = os.path.join(target_dir, f"video_scene_{scene_id}.mp4")

        # Fallback de segurança: Se a IA mandar uma query muito louca e voltar 0 resultados, 
        # nós substituímos por algo genérico para o vídeo não quebrar.
        fallback_queries = ["abstract technology", "cyber network", "dark matrix code"]

        video_url = self._fetch_video_url(query)
        
        # Se não achou, tenta os fallbacks
        if not video_url:
            logger.warning(f"Nenhum vídeo encontrado para '{query}'. Tentando fallbacks...")
            for f_query in fallback_queries:
                video_url = self._fetch_video_url(f_query)
                if video_url:
                    break
                    
        if not video_url:
            return {"status": "error", "message": "Nenhum vídeo encontrado nem nos fallbacks."}

        # Faz o download real do arquivo .mp4
        try:
            logger.info(f"Baixando vídeo da Cena {scene_id}...")
            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            # Escreve o arquivo em chunks para não estourar a RAM
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Vídeo da Cena {scene_id} baixado com sucesso.")
            return {"status": "success", "file_path": output_path}
            
        except Exception as e:
            logger.error(f"Erro no download do vídeo da cena {scene_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _fetch_video_url(self, query: str) -> str:
        """Faz a requisição na API do Pexels e extrai o link do .mp4 em HD."""
        params = {
            "query": query,
            "orientation": "landscape", # Força 16:9
            "size": "medium", # Tenta pegar 1080p ou 720p para evitar arquivos de 4K gigantes
            "per_page": 3 # Pega os 3 primeiros para ter opções
        }

        try:
            response = requests.get(self.base_url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get("videos"):
                return None

            # Pega o primeiro vídeo da lista
            first_video = data["videos"][0]
            
            # Procura pelo arquivo de vídeo com qualidade HD (evita SD e 4K)
            video_files = first_video.get("video_files", [])
            for f in video_files:
                if f["quality"] == "hd":
                    return f["link"]
            
            # Se não achar HD, pega o primeiro link disponível
            return video_files[0]["link"] if video_files else None

        except Exception as e:
            logger.error(f"Erro na API do Pexels: {str(e)}")
            return None