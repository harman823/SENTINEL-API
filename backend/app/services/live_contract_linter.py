from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.services.pr_remediation_bot import DriftRemediationPatchBuilder


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


@dataclass
class ResponseShape:
    method: str
    path: str
    line: int
    keys: Set[str]


class LiveContractLinter:
    """Validate edited endpoint response shapes against an OpenAPI spec."""

    @classmethod
    def lint_file(cls, source_path: str, spec_raw: Dict[str, Any]) -> Dict[str, Any]:
        path = Path(source_path)
        content = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".py":
            shapes = cls._python_response_shapes(content)
        elif path.suffix.lower() in {".js", ".ts"}:
            shapes = cls._js_response_shapes(content)
        else:
            shapes = []

        diagnostics: List[Dict[str, Any]] = []
        for shape in shapes:
            expected = cls._response_schema_properties(spec_raw, shape.path, shape.method)
            if expected is None:
                continue

            expected_keys, required_keys, schema_path = expected
            extra_keys = sorted(shape.keys - expected_keys)
            missing_required = sorted(required_keys - shape.keys)

            for key in extra_keys:
                patch = {
                    "target": "openapi",
                    "format": "json_patch",
                    "operations": [
                        {
                            "op": "add",
                            "path": DriftRemediationPatchBuilder._pointer(schema_path + ["properties", key]),
                            "value": {"type": "string"},
                        }
                    ],
                }
                diagnostics.append(
                    {
                        "code": "sentinel.extra_response_field",
                        "severity": "error",
                        "message": (
                            f"{shape.method.upper()} {shape.path} returns '{key}', "
                            "but the field is not documented in OpenAPI."
                        ),
                        "file": source_path,
                        "line": shape.line,
                        "character": 0,
                        "endpoint": f"{shape.method.upper()} {shape.path}",
                        "field": key,
                        "remediation_patch": patch,
                    }
                )

            for key in missing_required:
                diagnostics.append(
                    {
                        "code": "sentinel.missing_required_response_field",
                        "severity": "error",
                        "message": (
                            f"{shape.method.upper()} {shape.path} does not return required "
                            f"OpenAPI field '{key}'."
                        ),
                        "file": source_path,
                        "line": shape.line,
                        "character": 0,
                        "endpoint": f"{shape.method.upper()} {shape.path}",
                        "field": key,
                    }
                )

        return {"diagnostics": diagnostics, "count": len(diagnostics)}

    @classmethod
    def apply_spec_patch(cls, spec_path: str, remediation_patch: Dict[str, Any]) -> Dict[str, Any]:
        import yaml

        path = Path(spec_path)
        raw = path.read_text(encoding="utf-8")
        spec_raw = json.loads(raw) if path.suffix.lower() == ".json" else yaml.safe_load(raw)
        updated = DriftRemediationPatchBuilder.apply_to_spec(spec_raw, remediation_patch)
        if path.suffix.lower() == ".json":
            path.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
        else:
            path.write_text(yaml.safe_dump(updated, sort_keys=False), encoding="utf-8")
        return {"success": True, "spec_path": str(path), "operations": len(remediation_patch.get("operations", []))}

    @classmethod
    def _python_response_shapes(cls, content: str) -> List[ResponseShape]:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        shapes: List[ResponseShape] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            routes = cls._python_routes_for_function(node)
            if not routes:
                continue
            for return_node in [item for item in ast.walk(node) if isinstance(item, ast.Return)]:
                keys = cls._python_dict_keys(return_node.value)
                if not keys:
                    continue
                for method, route_path in routes:
                    shapes.append(ResponseShape(method=method, path=route_path, line=return_node.lineno, keys=keys))
        return shapes

    @classmethod
    def _python_routes_for_function(cls, node: ast.AST) -> List[Tuple[str, str]]:
        routes: List[Tuple[str, str]] = []
        decorators = getattr(node, "decorator_list", [])
        for decorator in decorators:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr.lower()
            if method not in HTTP_METHODS and method not in {"route", "api_route"}:
                continue
            route_path = cls._string_value(decorator.args[0]) if decorator.args else None
            if not route_path:
                continue
            methods = [method] if method in HTTP_METHODS else cls._python_methods_from_keywords(decorator)
            for item in methods:
                routes.append((item, cls._normalize_route_path(route_path)))
        return routes

    @staticmethod
    def _python_methods_from_keywords(call: ast.Call) -> List[str]:
        for keyword in call.keywords:
            if keyword.arg != "methods":
                continue
            value = keyword.value
            if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
                methods = []
                for item in value.elts:
                    raw = LiveContractLinter._string_value(item)
                    if raw:
                        methods.append(raw.lower())
                return methods or ["get"]
        return ["get"]

    @staticmethod
    def _python_dict_keys(node: Optional[ast.AST]) -> Set[str]:
        if isinstance(node, ast.Dict):
            keys: Set[str] = set()
            for key in node.keys:
                value = LiveContractLinter._string_value(key)
                if value:
                    keys.add(value)
            return keys
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"dict", "JSONResponse"}:
            if node.func.id == "dict":
                return {kw.arg for kw in node.keywords if kw.arg}
            for keyword in node.keywords:
                if keyword.arg == "content":
                    return LiveContractLinter._python_dict_keys(keyword.value)
        return set()

    @classmethod
    def _js_response_shapes(cls, content: str) -> List[ResponseShape]:
        shapes: List[ResponseShape] = []
        route_pattern = re.compile(
            r"""\b(?:app|router|server)\.(?P<method>get|post|put|patch|delete|options|head)\(\s*['"`](?P<path>[^'"`]+)['"`](?P<body>.*?)\n\s*\}\s*\)""",
            re.IGNORECASE | re.DOTALL,
        )
        for route_match in route_pattern.finditer(content):
            body = route_match.group("body")
            response_match = re.search(r"""\b(?:res\.json|reply\.send|return)\s*\(?\s*\{(?P<object>.*?)\}""", body, re.DOTALL)
            if not response_match:
                continue
            keys = set(re.findall(r"""['"`]?([A-Za-z_$][\w$-]*)['"`]?\s*:""", response_match.group("object")))
            if not keys:
                continue
            line = content[: route_match.start()].count("\n") + body[: response_match.start()].count("\n") + 1
            shapes.append(
                ResponseShape(
                    method=route_match.group("method").lower(),
                    path=cls._normalize_route_path(route_match.group("path")),
                    line=line,
                    keys=keys,
                )
            )
        return shapes

    @staticmethod
    def _response_schema_properties(
        spec_raw: Dict[str, Any],
        route_path: str,
        method: str,
    ) -> Optional[Tuple[Set[str], Set[str], List[str]]]:
        operation = spec_raw.get("paths", {}).get(route_path, {}).get(method.lower())
        if not isinstance(operation, dict):
            return None
        responses = operation.get("responses", {})
        if not isinstance(responses, dict):
            return None
        response_code = "200" if "200" in responses else next(iter(responses), None)
        if not response_code:
            return None
        content = responses.get(response_code, {}).get("content", {})
        if not isinstance(content, dict):
            return None
        for content_type, media in content.items():
            if "json" not in content_type or not isinstance(media, dict):
                continue
            schema = media.get("schema", {})
            if not isinstance(schema, dict):
                continue
            properties = schema.get("properties", {})
            if not isinstance(properties, dict):
                return None
            required = schema.get("required", [])
            return (
                set(properties.keys()),
                set(required if isinstance(required, list) else []),
                ["paths", route_path, method.lower(), "responses", response_code, "content", content_type, "schema"],
            )
        return None

    @staticmethod
    def _string_value(node: Optional[ast.AST]) -> Optional[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Str):
            return node.s
        return None

    @staticmethod
    def _normalize_route_path(path: str) -> str:
        normalized = path.strip() or "/"
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        normalized = re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", normalized)
        normalized = re.sub(r":([A-Za-z_][A-Za-z0-9_]*)", r"{\1}", normalized)
        normalized = re.sub(r"//+", "/", normalized)
        return normalized
