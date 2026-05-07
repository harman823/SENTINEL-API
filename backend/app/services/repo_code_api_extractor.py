from __future__ import annotations

import ast
import re
from typing import Any, Dict, List, Optional, Set, Tuple


SOURCE_EXTENSIONS = {".py", ".js", ".ts"}
SKIP_PATH_PARTS = {
    "node_modules",
    ".next",
    "dist",
    "build",
    "coverage",
    "venv",
    "__pycache__",
}
FRAMEWORK_NAMES = {
    "fastapi": "FastAPI",
    "flask": "Flask",
    "starlette": "Starlette",
    "django": "Django",
    "express": "Express",
    "fastify": "Fastify",
    "bottle": "Bottle",
    "sanic": "Sanic",
}
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
PRIORITY_FILE_HINTS = ("api", "app", "main", "server", "route", "router", "view", "endpoint", "controller")


class RepoCodeApiExtractor:
    @staticmethod
    def _extension(path: str) -> str:
        dot = path.rfind(".")
        return path[dot:].lower() if dot >= 0 else ""

    @classmethod
    def is_candidate_source_file(cls, path: str) -> bool:
        parts = {part.lower() for part in path.split("/")}
        if parts & SKIP_PATH_PARTS:
            return False
        lower = path.lower()
        if any(part in lower for part in (".min.js", ".bundle.js", ".spec.", ".test.")):
            return False
        return cls._extension(path) in SOURCE_EXTENSIONS

    @staticmethod
    def _path_priority(path: str) -> Tuple[int, int, str]:
        lower = path.lower()
        hint_score = sum(1 for hint in PRIORITY_FILE_HINTS if hint in lower)
        depth = lower.count("/")
        return (-hint_score, depth, lower)

    @classmethod
    def select_source_files(cls, file_paths: List[str], limit: int = 60) -> List[str]:
        candidates = [path for path in file_paths if cls.is_candidate_source_file(path)]
        candidates.sort(key=cls._path_priority)
        return candidates[:limit]

    @staticmethod
    def _string_value(node: Optional[ast.AST]) -> Optional[str]:
        if node is None:
            return None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Str):
            return node.s
        return None

    @classmethod
    def _list_of_strings(cls, node: Optional[ast.AST]) -> List[str]:
        if node is None:
            return []
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            values = []
            for item in node.elts:
                value = cls._string_value(item)
                if value:
                    values.append(value.upper())
            return values
        value = cls._string_value(node)
        return [value.upper()] if value else []

    @staticmethod
    def _callee_name(node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    @staticmethod
    def _dotted_name(node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            root = RepoCodeApiExtractor._dotted_name(node.value)
            return f"{root}.{node.attr}" if root else node.attr
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

    @classmethod
    def _join_paths(cls, prefix: str, path: str) -> str:
        if not prefix:
            return cls._normalize_route_path(path)
        combined = f"{prefix.rstrip('/')}/{path.lstrip('/')}"
        return cls._normalize_route_path(combined)

    @classmethod
    def _extract_python_routes(cls, path: str, content: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return [], []

        imported_modules: Set[str] = set()
        imported_names: Dict[str, str] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name.split(".")[0])
                    imported_names[alias.asname or alias.name.split(".")[-1]] = alias.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module.split(".")[0])
                for alias in node.names:
                    imported_names[alias.asname or alias.name] = f"{node.module}.{alias.name}"

        frameworks: Set[str] = set()
        for module_name, label in FRAMEWORK_NAMES.items():
            if module_name in imported_modules or any(value.startswith(module_name) for value in imported_names.values()):
                frameworks.add(label)

        object_meta: Dict[str, Dict[str, Any]] = {}
        urlpatterns: List[ast.AST] = []

        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                target_name = node.targets[0].id
                if isinstance(node.value, ast.Call):
                    callee = cls._callee_name(node.value.func)
                    if callee in {"FastAPI", "Flask", "APIRouter", "Blueprint", "Starlette", "Bottle", "Sanic"}:
                        prefix = ""
                        for keyword in node.value.keywords:
                            if keyword.arg in {"prefix", "url_prefix"}:
                                prefix = cls._string_value(keyword.value) or prefix
                        object_meta[target_name] = {
                            "kind": callee,
                            "prefix": prefix,
                        }
                if target_name == "urlpatterns" and isinstance(node.value, (ast.List, ast.Tuple)):
                    urlpatterns = list(node.value.elts)

            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr in {"register_blueprint", "include_router"}:
                    if call.args and isinstance(call.args[0], ast.Name):
                        router_name = call.args[0].id
                        router_meta = object_meta.get(router_name)
                        if router_meta:
                            for keyword in call.keywords:
                                if keyword.arg in {"url_prefix", "prefix"}:
                                    router_meta["prefix"] = cls._join_paths(
                                        router_meta.get("prefix", ""),
                                        cls._string_value(keyword.value) or "",
                                    )

        routes: List[Dict[str, Any]] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                        continue
                    owner = decorator.func.value
                    if not isinstance(owner, ast.Name):
                        continue
                    owner_name = owner.id
                    owner_meta = object_meta.get(owner_name)
                    if not owner_meta:
                        continue

                    decorator_name = decorator.func.attr
                    methods: List[str] = []
                    if decorator_name in HTTP_METHODS:
                        methods = [decorator_name.upper()]
                    elif decorator_name == "route":
                        methods = ["GET"]
                        for keyword in decorator.keywords:
                            if keyword.arg == "methods":
                                methods = cls._list_of_strings(keyword.value) or methods
                    elif decorator_name == "api_route":
                        for keyword in decorator.keywords:
                            if keyword.arg == "methods":
                                methods = cls._list_of_strings(keyword.value)
                        methods = methods or ["GET"]
                    else:
                        continue

                    raw_path = cls._string_value(decorator.args[0]) if decorator.args else None
                    if raw_path is None:
                        for keyword in decorator.keywords:
                            if keyword.arg in {"path", "rule"}:
                                raw_path = cls._string_value(keyword.value)
                    if not raw_path:
                        continue

                    full_path = cls._join_paths(owner_meta.get("prefix", ""), raw_path)
                    framework_name = {
                        "FastAPI": "FastAPI",
                        "APIRouter": "FastAPI",
                        "Flask": "Flask",
                        "Blueprint": "Flask",
                        "Starlette": "Starlette",
                        "Bottle": "Bottle",
                        "Sanic": "Sanic",
                    }.get(owner_meta["kind"], owner_meta["kind"])

                    frameworks.add(framework_name)
                    for method in methods:
                        routes.append(
                            {
                                "framework": framework_name,
                                "method": method,
                                "path": full_path,
                                "source_file": path,
                                "handler_name": node.name,
                                "summary": ast.get_docstring(node),
                            }
                        )

        for entry in urlpatterns:
            if not isinstance(entry, ast.Call):
                continue
            callee = cls._dotted_name(entry.func)
            if callee not in {"path", "re_path", "django.urls.path", "django.urls.re_path"}:
                continue
            route_value = cls._string_value(entry.args[0]) if entry.args else None
            if not route_value:
                continue
            routes.append(
                {
                    "framework": "Django",
                    "method": "GET",
                    "path": cls._normalize_route_path(route_value),
                    "source_file": path,
                    "handler_name": cls._dotted_name(entry.args[1]) if len(entry.args) > 1 else None,
                }
            )
            frameworks.add("Django")

        return sorted(frameworks), routes

    @classmethod
    def _extract_js_routes(cls, path: str, content: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        frameworks: Set[str] = set()
        routes: List[Dict[str, Any]] = []
        lower = content.lower()

        if "express" in lower:
            frameworks.add("Express")
        if "fastify" in lower:
            frameworks.add("Fastify")
        if "koa" in lower:
            frameworks.add("Koa")
        if "hono" in lower:
            frameworks.add("Hono")
        if "@nestjs" in lower:
            frameworks.add("NestJS")

        router_prefixes: Dict[str, str] = {}
        framework_objects: Dict[str, str] = {}

        for match in re.finditer(r"""\b(?:const|let|var)\s+(?P<object>[A-Za-z_$][\w$]*)\s*=\s*(?:require\(['"`]express['"`]\)|express\(\))""", content):
            framework_objects[match.group("object")] = "Express"
            frameworks.add("Express")
        for match in re.finditer(r"""\b(?:const|let|var)\s+(?P<object>[A-Za-z_$][\w$]*)\s*=\s*(?:require\(['"`]fastify['"`]\)|fastify)\s*\(""", content):
            framework_objects[match.group("object")] = "Fastify"
            frameworks.add("Fastify")
        for match in re.finditer(r"""\b(?:const|let|var)\s+(?P<router>[A-Za-z_$][\w$]*)\s*=\s*express\.Router\(""", content):
            framework_objects[match.group("router")] = "Express"
            frameworks.add("Express")

        for match in re.finditer(
            r"""\b(?:app|server|api|router)\.use\(\s*['"`](?P<prefix>[^'"`]+)['"`]\s*,\s*(?P<router>[A-Za-z_$][\w$]*)\s*\)""",
            content,
        ):
            router_prefixes[match.group("router")] = cls._normalize_route_path(match.group("prefix"))

        # NestJS decorators
        nest_pattern = re.compile(
            r"""@(?P<method>Get|Post|Put|Patch|Delete|Options|Head)\(\s*['"`](?P<path>[^'"`]+)['"`]\s*\)""",
            re.IGNORECASE,
        )
        for match in nest_pattern.finditer(content):
            routes.append(
                {
                    "framework": "NestJS",
                    "method": match.group("method").upper(),
                    "path": cls._normalize_route_path(match.group("path")),
                    "source_file": path,
                    "handler_name": None,
                }
            )

        route_pattern = re.compile(
            r"""\b(?P<object>[A-Za-z_$][\w$]*)\.(?P<method>get|post|put|patch|delete|options|head)\(\s*['"`](?P<path>[^'"`]+)['"`]""",
            re.IGNORECASE,
        )
        for match in route_pattern.finditer(content):
            object_name = match.group("object")
            route_path = cls._normalize_route_path(match.group("path"))
            full_path = cls._join_paths(router_prefixes.get(object_name, ""), route_path)
            framework = framework_objects.get(object_name)
            if not framework:
                if "fastify" in lower and object_name.lower() in {"fastify", "server"}:
                    framework = "Fastify"
                elif "koa" in lower and object_name.lower() in {"app", "router"}:
                    framework = "Koa"
                elif "hono" in lower and object_name.lower() in {"app", "hono"}:
                    framework = "Hono"
                else:
                    framework = "Express"
            routes.append(
                {
                    "framework": framework,
                    "method": match.group("method").upper(),
                    "path": full_path,
                    "source_file": path,
                    "handler_name": None,
                }
            )

        fastify_route_pattern = re.compile(
            r"""\b(?P<object>[A-Za-z_$][\w$]*)\.route\(\s*\{(?P<body>.*?)\}\s*\)""",
            re.IGNORECASE | re.DOTALL,
        )
        for match in fastify_route_pattern.finditer(content):
            body = match.group("body")
            method_match = re.search(r"""\bmethod\s*:\s*['"`](?P<method>[A-Za-z]+)['"`]""", body)
            path_match = re.search(r"""\b(?:url|path)\s*:\s*['"`](?P<path>[^'"`]+)['"`]""", body)
            if not method_match or not path_match:
                continue
            routes.append(
                {
                    "framework": "Fastify",
                    "method": method_match.group("method").upper(),
                    "path": cls._normalize_route_path(path_match.group("path")),
                    "source_file": path,
                    "handler_name": None,
                }
            )
            frameworks.add("Fastify")

        return sorted(frameworks), routes

    @classmethod
    def analyze_repo_sources(cls, file_contents: Dict[str, str]) -> Dict[str, Any]:
        all_routes: List[Dict[str, Any]] = []
        frameworks: Dict[str, Dict[str, Any]] = {}

        for path, content in file_contents.items():
            ext = cls._extension(path)
            if ext == ".py":
                detected_frameworks, routes = cls._extract_python_routes(path, content)
            elif ext in {".js", ".ts"}:
                detected_frameworks, routes = cls._extract_js_routes(path, content)
            else:
                detected_frameworks, routes = [], []

            for framework_name in detected_frameworks:
                meta = frameworks.setdefault(
                    framework_name,
                    {"framework": framework_name, "files": set(), "routes": 0},
                )
                meta["files"].add(path)

            for route in routes:
                meta = frameworks.setdefault(
                    route["framework"],
                    {"framework": route["framework"], "files": set(), "routes": 0},
                )
                meta["files"].add(path)
                meta["routes"] += 1
                all_routes.append(route)

        deduped_routes: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        for route in all_routes:
            key = (route["framework"], route["method"], route["path"])
            deduped_routes.setdefault(key, route)

        for item in frameworks.values():
            item["routes"] = 0
        for route in deduped_routes.values():
            frameworks[route["framework"]]["routes"] += 1

        framework_list = [
            {
                "framework": item["framework"],
                "files": sorted(item["files"]),
                "route_count": item["routes"],
            }
            for item in frameworks.values()
        ]
        framework_list.sort(key=lambda item: (-item["route_count"], item["framework"]))

        routes = list(deduped_routes.values())
        routes.sort(key=lambda item: (item["path"], item["method"], item["framework"]))

        return {
            "frameworks": framework_list,
            "routes": routes,
            "summary": {
                "framework_count": len(framework_list),
                "route_count": len(routes),
            },
        }

    @classmethod
    def synthesize_openapi_spec(
        cls,
        repo_name: str,
        repo_description: Optional[str],
        code_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        routes = code_analysis.get("routes", [])
        if not routes:
            raise ValueError("No framework routes were extracted from source code.")

        frameworks = [item["framework"] for item in code_analysis.get("frameworks", [])]
        paths: Dict[str, Dict[str, Any]] = {}

        for route in routes:
            path = cls._normalize_route_path(route["path"])
            method = route["method"].lower()
            handler_name = route.get("handler_name")
            framework_name = route["framework"]
            operation_id = handler_name or f"{method}_{path.strip('/').replace('/', '_').replace('{', '').replace('}', '') or 'root'}"
            route_summary = route.get("summary")

            paths.setdefault(path, {})[method] = {
                "summary": handler_name or f"{framework_name} inferred route",
                "description": route_summary or f"Code-inferred endpoint extracted from {route['source_file']} via {framework_name}.",
                "operationId": operation_id,
                "responses": {
                    "200": {"description": "Successful response (inferred from source code)"}
                },
                "x-sentinel-source": {
                    "type": "code",
                    "framework": framework_name,
                    "source_file": route["source_file"],
                },
            }

        return {
            "openapi": "3.0.0",
            "info": {
                "title": f"{repo_name} Code-Inferred API",
                "version": "source-derived",
                "description": repo_description or (
                    f"OpenAPI document synthesized from framework source code: {', '.join(frameworks)}"
                ),
            },
            "paths": paths,
            "x-sentinel-code-analysis": code_analysis,
        }
