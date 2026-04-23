import os
import json
import re
from datetime import datetime
from unicodedata import normalize

class ProjectManager:
    def __init__(self):
        self.base_output = os.path.join(os.getcwd(), "outputs")
        os.makedirs(self.base_output, exist_ok=True)

    def _slugify(self, text: str) -> str:
        # Transforma o tema em um nome de pasta seguro
        text = normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        text = re.sub(r'[^\w\s-]', '', text).strip().lower()
        return re.sub(r'[-\s]+', '-', text)

    def create_project_structure(self, theme: str) -> dict:
        date_str = datetime.now().strftime("%Y-%m-%d")
        slug = self._slugify(theme)
        project_name = f"{date_str}_{slug}"
        project_path = os.path.join(self.base_output, project_name)

        # Criar subpastas
        paths = {
            "root": project_path,
            "audio": os.path.join(project_path, "audio"),
            "video": os.path.join(project_path, "video"),
            "script": os.path.join(project_path, "script.json")
        }

        for path in [paths["root"], paths["audio"], paths["video"]]:
            os.makedirs(path, exist_ok=True)

        return paths

    def save_script(self, path: str, data: dict):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)