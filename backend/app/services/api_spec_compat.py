from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Dict, List, Optional


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


class ApiSpecCompat:
    """Normalize supported API documentation formats into Sentinel's OpenAPI 3 shape."""

    @staticmethod
    def detect_format(spec: Dict[str, Any]) -> Dict[str, Optional[str]]:
        if not isinstance(spec, dict):
            return {"kind": None, "version": None}
        openapi_version = spec.get("openapi")
        if isinstance(openapi_version, str):
            return {"kind": "openapi", "version": openapi_version}
        swagger_version = spec.get("swagger")
        if isinstance(swagger_version, str):
            return {"kind": "swagger", "version": swagger_version}
        
        # Other major api documentations
        if "asyncapi" in spec:
            return {"kind": "asyncapi", "version": spec.get("asyncapi")}
        if "raml" in spec or spec.get("title", "").lower().endswith("raml"):
             return {"kind": "raml", "version": None}

        info = spec.get("info")
        schema = info.get("schema") if isinstance(info, dict) else None
        if isinstance(schema, str) and "schema.getpostman.com/json/collection" in schema:
            return {"kind": "postman", "version": schema.rsplit("/", 1)[-1]}
        if spec.get("_type") == "export" and isinstance(spec.get("resources"), list):
            return {"kind": "insomnia", "version": str(spec.get("__export_format") or "")}
        if "info" in spec and "paths" in spec:
            return {"kind": "openapi-like", "version": None}
        return {"kind": None, "version": None}

    @classmethod
    def to_openapi3(cls, spec: Dict[str, Any]) -> Dict[str, Any]:
        fmt = cls.detect_format(spec)
        kind = fmt.get("kind")
        if kind == "openapi":
            return deepcopy(spec)
        if kind == "swagger":
            return cls._swagger2_to_openapi3(spec)
        if kind == "postman":
            return cls._postman_to_openapi3(spec)
        if kind == "insomnia":
            return cls._insomnia_to_openapi3(spec)
        if kind == "asyncapi":
            return cls._asyncapi_to_openapi3(spec)
        if kind in ("openapi-like", "raml"):
            converted = deepcopy(spec)
            converted.setdefault("openapi", "3.0.0")
            return converted
        raise ValueError(cls.unsupported_message(spec))

    @classmethod
    def unsupported_message(cls, spec: Dict[str, Any]) -> str:
        return "Unsupported API documentation format. Sentinel supports OpenAPI, Swagger, Postman, Insomnia, AsyncAPI, and RAML documents."

    @classmethod
    def _asyncapi_to_openapi3(cls, spec: Dict[str, Any]) -> Dict[str, Any]:
        converted: Dict[str, Any] = {
            "openapi": "3.0.0",
            "info": deepcopy(spec.get("info", {"title": "AsyncAPI", "version": "unknown"})),
            "paths": {},
            "x-sentinel-original-format": {
                "kind": "asyncapi",
                "version": spec.get("asyncapi"),
            },
        }
        for channel, channel_item in spec.get("channels", {}).items():
            if not isinstance(channel_item, dict):
                continue
            path = channel
            if not path.startswith("/"):
                path = "/" + path
            converted["paths"].setdefault(path, {})
            if "publish" in channel_item:
                converted["paths"][path]["post"] = {
                    "summary": channel_item["publish"].get("summary", "Publish message"),
                    "responses": {"200": {"description": "Message published"}}
                }
            if "subscribe" in channel_item:
                converted["paths"][path]["get"] = {
                    "summary": channel_item["subscribe"].get("summary", "Subscribe to messages"),
                    "responses": {"200": {"description": "Message received"}}
                }
        return converted

    @classmethod
    def _swagger2_to_openapi3(cls, spec: Dict[str, Any]) -> Dict[str, Any]:
        converted: Dict[str, Any] = {
            "openapi": "3.0.0",
            "info": deepcopy(spec.get("info", {"title": "Swagger API", "version": "unknown"})),
            "paths": {},
            "components": {},
            "x-sentinel-original-format": {
                "kind": "swagger",
                "version": spec.get("swagger"),
            },
        }

        servers = cls._servers_from_swagger(spec)
        if servers:
            converted["servers"] = servers

        definitions = spec.get("definitions")
        if isinstance(definitions, dict):
            converted["components"]["schemas"] = deepcopy(definitions)

        security_definitions = spec.get("securityDefinitions")
        if isinstance(security_definitions, dict):
            converted["components"]["securitySchemes"] = deepcopy(security_definitions)

        if isinstance(spec.get("security"), list):
            converted["security"] = deepcopy(spec["security"])

        produces = cls._string_list(spec.get("produces")) or ["application/json"]
        consumes = cls._string_list(spec.get("consumes")) or ["application/json"]
        global_parameters = spec.get("parameters", {})

        for path, path_item in spec.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            converted_path: Dict[str, Any] = {}
            path_parameters = path_item.get("parameters", [])
            for method, operation in path_item.items():
                method_lower = method.lower()
                if method_lower not in HTTP_METHODS or not isinstance(operation, dict):
                    continue
                converted_path[method_lower] = cls._convert_operation(
                    operation=operation,
                    path_parameters=path_parameters,
                    global_parameters=global_parameters,
                    consumes=cls._string_list(operation.get("consumes")) or consumes,
                    produces=cls._string_list(operation.get("produces")) or produces,
                )
            if converted_path:
                converted["paths"][path] = converted_path

        if not converted["components"]:
            converted.pop("components")
        return converted

    @staticmethod
    def _servers_from_swagger(spec: Dict[str, Any]) -> List[Dict[str, str]]:
        host = spec.get("host")
        base_path = spec.get("basePath", "")
        schemes = spec.get("schemes") if isinstance(spec.get("schemes"), list) else []
        if not host:
            return []
        return [{"url": f"{scheme}://{host}{base_path}"} for scheme in schemes or ["https"]]

    @staticmethod
    def _string_list(value: Any) -> List[str]:
        return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []

    @classmethod
    def _resolve_parameter(cls, parameter: Dict[str, Any], global_parameters: Dict[str, Any]) -> Dict[str, Any]:
        ref = parameter.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/parameters/"):
            name = ref.rsplit("/", 1)[-1]
            target = global_parameters.get(name)
            if isinstance(target, dict):
                return deepcopy(target)
        return deepcopy(parameter)

    @classmethod
    def _convert_operation(
        cls,
        operation: Dict[str, Any],
        path_parameters: Any,
        global_parameters: Dict[str, Any],
        consumes: List[str],
        produces: List[str],
    ) -> Dict[str, Any]:
        converted = {
            key: deepcopy(value)
            for key, value in operation.items()
            if key not in {"parameters", "responses", "consumes", "produces", "schemes"}
        }

        parameters: List[Dict[str, Any]] = []
        body_schema: Optional[Dict[str, Any]] = None
        form_properties: Dict[str, Any] = {}
        required_form_fields: List[str] = []

        raw_parameters = []
        if isinstance(path_parameters, list):
            raw_parameters.extend(path_parameters)
        if isinstance(operation.get("parameters"), list):
            raw_parameters.extend(operation["parameters"])

        for raw_parameter in raw_parameters:
            if not isinstance(raw_parameter, dict):
                continue
            parameter = cls._resolve_parameter(raw_parameter, global_parameters)
            location = parameter.get("in")
            if location == "body":
                schema = parameter.get("schema")
                if isinstance(schema, dict):
                    body_schema = deepcopy(schema)
                continue
            if location == "formData":
                name = parameter.get("name")
                if isinstance(name, str):
                    form_properties[name] = cls._parameter_schema(parameter)
                    if parameter.get("required"):
                        required_form_fields.append(name)
                continue
            if location in {"query", "path", "header", "cookie"}:
                converted_parameter = {
                    key: deepcopy(value)
                    for key, value in parameter.items()
                    if key not in {"type", "format", "items", "collectionFormat"}
                }
                converted_parameter["schema"] = cls._parameter_schema(parameter)
                parameters.append(converted_parameter)

        if parameters:
            converted["parameters"] = parameters
        if body_schema:
            converted["requestBody"] = cls._request_body(body_schema, consumes)
        elif form_properties:
            schema: Dict[str, Any] = {"type": "object", "properties": form_properties}
            if required_form_fields:
                schema["required"] = required_form_fields
            converted["requestBody"] = cls._request_body(schema, ["application/x-www-form-urlencoded"])

        converted["responses"] = cls._convert_responses(operation.get("responses", {}), produces)
        return converted

    @staticmethod
    def _parameter_schema(parameter: Dict[str, Any]) -> Dict[str, Any]:
        schema = parameter.get("schema")
        if isinstance(schema, dict):
            return deepcopy(schema)
        return {
            key: deepcopy(parameter[key])
            for key in ("type", "format", "items", "default", "enum", "minimum", "maximum")
            if key in parameter
        } or {"type": "string"}

    @staticmethod
    def _request_body(schema: Dict[str, Any], content_types: List[str]) -> Dict[str, Any]:
        return {
            "required": False,
            "content": {
                content_type: {"schema": deepcopy(schema)}
                for content_type in content_types
            },
        }

    @classmethod
    def _convert_responses(cls, responses: Any, produces: List[str]) -> Dict[str, Any]:
        if not isinstance(responses, dict):
            return {"default": {"description": "Response"}}
        converted: Dict[str, Any] = {}
        for status, response in responses.items():
            if not isinstance(response, dict):
                converted[status] = {"description": str(response)}
                continue
            response_copy = {
                key: deepcopy(value)
                for key, value in response.items()
                if key not in {"schema", "examples"}
            }
            schema = response.get("schema")
            if isinstance(schema, dict):
                response_copy["content"] = {
                    content_type: {"schema": deepcopy(schema)}
                    for content_type in produces
                }
            converted[status] = response_copy
        return converted or {"default": {"description": "Response"}}

    @classmethod
    def _postman_to_openapi3(cls, spec: Dict[str, Any]) -> Dict[str, Any]:
        info = spec.get("info") if isinstance(spec.get("info"), dict) else {}
        converted = cls._empty_synthetic_doc(
            title=info.get("name") or "Postman Collection API",
            version="postman-derived",
            source_kind="postman",
            source_version=info.get("schema"),
            description=info.get("description") if isinstance(info.get("description"), str) else None,
        )
        for item in spec.get("item", []):
            cls._walk_postman_item(item, converted["paths"])
        return converted

    @classmethod
    def _walk_postman_item(cls, item: Any, paths: Dict[str, Any]) -> None:
        if not isinstance(item, dict):
            return
        if isinstance(item.get("item"), list):
            for child in item["item"]:
                cls._walk_postman_item(child, paths)
            return

        request = item.get("request")
        if isinstance(request, str):
            method = "GET"
            path = cls._url_to_path(request)
        elif isinstance(request, dict):
            method = str(request.get("method") or "GET").lower()
            path = cls._url_to_path(request.get("url"))
        else:
            return
        if method not in HTTP_METHODS or not path:
            return
        paths.setdefault(path, {})[method] = {
            "summary": item.get("name") or f"{method.upper()} {path}",
            "description": "Endpoint inferred from a Postman collection.",
            "operationId": cls._operation_id(method, path, item.get("name")),
            "responses": {"default": {"description": "Response documented in source collection"}},
            "x-sentinel-source": {"type": "api-documentation", "format": "postman"},
        }

    @classmethod
    def _insomnia_to_openapi3(cls, spec: Dict[str, Any]) -> Dict[str, Any]:
        converted = cls._empty_synthetic_doc(
            title="Insomnia Export API",
            version="insomnia-derived",
            source_kind="insomnia",
            source_version=str(spec.get("__export_format") or ""),
            description=None,
        )
        for resource in spec.get("resources", []):
            if not isinstance(resource, dict) or resource.get("_type") != "request":
                continue
            method = str(resource.get("method") or "GET").lower()
            path = cls._url_to_path(resource.get("url"))
            if method not in HTTP_METHODS or not path:
                continue
            converted["paths"].setdefault(path, {})[method] = {
                "summary": resource.get("name") or f"{method.upper()} {path}",
                "description": "Endpoint inferred from an Insomnia export.",
                "operationId": cls._operation_id(method, path, resource.get("name")),
                "responses": {"default": {"description": "Response documented in source export"}},
                "x-sentinel-source": {"type": "api-documentation", "format": "insomnia"},
            }
        return converted

    @staticmethod
    def _empty_synthetic_doc(
        title: str,
        version: str,
        source_kind: str,
        source_version: Optional[str],
        description: Optional[str],
    ) -> Dict[str, Any]:
        return {
            "openapi": "3.0.0",
            "info": {
                "title": title,
                "version": version,
                "description": description or f"OpenAPI document synthesized from {source_kind} API documentation.",
            },
            "paths": {},
            "x-sentinel-original-format": {
                "kind": source_kind,
                "version": source_version,
            },
        }

    @staticmethod
    def _url_to_path(url_value: Any) -> Optional[str]:
        if isinstance(url_value, dict):
            raw_path = url_value.get("path")
            if isinstance(raw_path, list):
                path = "/" + "/".join(str(part).strip("/") for part in raw_path if str(part))
                return path.replace("{{", "{").replace("}}", "}") or "/"
            raw = url_value.get("raw")
        else:
            raw = url_value
        if not isinstance(raw, str) or not raw.strip():
            return None
        value = raw.strip().replace("{{baseUrl}}", "")
        for scheme in ("https://", "http://"):
            if value.startswith(scheme):
                without_scheme = value[len(scheme):]
                slash = without_scheme.find("/")
                value = without_scheme[slash:] if slash >= 0 else "/"
                break
        path = value.split("?", 1)[0] or "/"
        if not path.startswith("/"):
            path = f"/{path}"
        return path.replace("{{", "{").replace("}}", "}")

    @staticmethod
    def _operation_id(method: str, path: str, name: Any) -> str:
        if isinstance(name, str) and name.strip():
            base = re.sub(r"[^A-Za-z0-9_]+", "_", name.strip()).strip("_")
            if base:
                return base[:80]
        base = re.sub(r"[^A-Za-z0-9_]+", "_", path.strip("/")).strip("_") or "root"
        return f"{method}_{base}"[:80]
