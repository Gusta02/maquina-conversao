import os
import json
import logging
from groq import Groq

logger = logging.getLogger("app_logger")

class LLMEngine:
    def __init__(self):
        # A chave é puxada automaticamente do .env
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        # Usando o Llama 3 70B para melhor raciocínio lógico
        self.model = "llama-3.3-70b-versatile"

    def generate_script(self, theme: str, lang: str = "EN-US") -> dict:
        """
        Recebe um tema e retorna um roteiro estruturado em JSON.
        """
        logger.info(f"Iniciando geração de roteiro via LLM para o tema: {theme}")
        
        system_prompt = f"""
        You are an expert YouTube scriptwriter and video director for high-retention 'Dark Channels'.
        Your target audience is {lang}.
        Create a fast-paced, highly engaging video script about: '{theme}'.
        
        RULES:
        1. Break the video into short, dynamic scenes.
        2. 'narration' for each scene MUST NOT exceed 8 seconds when spoken (keep it punchy).
        3. 'search_query' must be 2-4 keywords in English for searching stock footage on Pexels (e.g., 'hacker typing', 'server room').
        4. The first scene MUST have a strong hook.
        5. Generate between 3 to 5 scenes for this test.
        
        OUTPUT FORMAT:
        You must reply ONLY with a valid JSON object. No markdown, no introductions, no explanations.
        Structure:
        {{
            "scenes": [
                {{
                    "id": 1,
                    "narration": "...",
                    "search_query": "..."
                }}
            ]
        }}
        """

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    }
                ],
                model=self.model,
                temperature=0.7,
            )
            
            # Extrair o conteúdo e forçar o parse para JSON
            response_text = chat_completion.choices[0].message.content.strip()
            
            # Limpeza de segurança caso a IA retorne blocos de markdown ```json
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
                
            script_data = json.loads(response_text)
            logger.info("Roteiro JSON gerado e parseado com sucesso.")
            
            return {
                "status": "success",
                "data": script_data
            }

        except json.JSONDecodeError as e:
            logger.error(f"Falha ao parsear JSON da IA. Retorno bruto: {response_text}")
            return {"status": "error", "message": "A IA não retornou um JSON válido."}
        except Exception as e:
            logger.error(f"Erro na API do LLM: {str(e)}")
            return {"status": "error", "message": str(e)}