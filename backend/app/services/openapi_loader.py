import yaml
import json
import os
from typing import Dict, Any

class OpenAPILoader:
    @staticmethod
    def load_spec(file_path: str) -> Dict[str, Any]:
        """
        Load an OpenAPI specification from a YAML or JSON file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Spec file not found: {file_path}")

        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        with open(file_path, 'r', encoding='utf-8') as f:
            if ext in ['.yaml', '.yml']:
                return OpenAPILoader._parse_yaml(f)
            elif ext == '.json':
                return OpenAPILoader._parse_json(f)
            else:
                raise ValueError(f"Unsupported file extension: {ext}. parsing only supports .yaml, .yml, .json")

    @staticmethod
    def _parse_yaml(f) -> Dict[str, Any]:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")

    @staticmethod
    def _parse_json(f) -> Dict[str, Any]:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
