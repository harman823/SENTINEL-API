import yaml
import json
import os
import httpx
from urllib.parse import urlparse
from typing import Dict, Any

class OpenAPILoader:
    @staticmethod
    def _convert_github_url_to_raw(url: str) -> str:
        """Convert various GitHub URL formats to raw content URLs."""
        # Already a raw URL — passthrough
        if "raw.githubusercontent.com" in url:
            return url
        # Standard blob URL: github.com/user/repo/blob/branch/path
        if "github.com" in url and "/blob/" in url:
            return url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        # Tree URL: github.com/user/repo/tree/branch/path (less common for single files)
        if "github.com" in url and "/tree/" in url:
            return url.replace("github.com", "raw.githubusercontent.com").replace("/tree/", "/")
        # Raw tab URL: github.com/user/repo/raw/branch/path
        if "github.com" in url and "/raw/" in url:
            return url.replace("github.com", "raw.githubusercontent.com").replace("/raw/", "/")
        # GitHub API URL: api.github.com/repos/user/repo/contents/path
        if "api.github.com" in url:
            # These return JSON by default; we need to add ?raw=1 or use Accept header
            if "?" not in url:
                return url + "?raw=1"
            return url + "&raw=1"
        return url

    @staticmethod
    def load_spec(file_path: str) -> Dict[str, Any]:
        """
        Load an OpenAPI specification from a YAML or JSON file, or a remote URL.
        """
        parsed_url = urlparse(file_path)
        if parsed_url.scheme in ('http', 'https'):
            load_url = OpenAPILoader._convert_github_url_to_raw(file_path)
            try:
                with httpx.Client(follow_redirects=True, timeout=15.0) as client:
                    response = client.get(load_url)
                    response.raise_for_status()
                    content = response.text
                    
                    # Try parsing as JSON first, then YAML
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        try:
                            return yaml.safe_load(content)
                        except yaml.YAMLError as e:
                            raise ValueError(f"Fetched content is neither valid JSON nor YAML: {e}")
            except httpx.RequestError as e:
                raise ValueError(f"Failed to fetch spec from URL: {e}")

        # Local file handling
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Spec file not found: {file_path}")

        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        with open(file_path, 'r', encoding='utf-8') as f:
            if ext in ['.yaml', '.yml']:
                return OpenAPILoader._parse_yaml(f.read())
            elif ext == '.json':
                return OpenAPILoader._parse_json(f.read())
            else:
                raise ValueError(f"Unsupported file extension: {ext}. parsing only supports .yaml, .yml, .json")

    @staticmethod
    def _parse_yaml(content: str) -> Dict[str, Any]:
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")

    @staticmethod
    def _parse_json(content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
