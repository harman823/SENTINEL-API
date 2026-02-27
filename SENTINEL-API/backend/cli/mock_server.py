import json
import logging
import uvicorn
from fastapi import FastAPI, Request, Response
from backend.app.services.openapi_loader import OpenAPILoader
from backend.app.services.spec_normalizer import SpecNormalizer
from backend.app.schemas.spec import NormalizedSpec
from backend.app.core.llm import get_llm_text
from typing import Dict, Any

logger = logging.getLogger(__name__)

class IntelligentMockServer:
    """
    Feature 7: Instant Intelligent Mock Server.
    Spins up a FastAPI server dynamically from an OpenAPI spec.
    Uses an in-memory state dictionary and deterministic logic (or lightweight LLM)
    to maintain state (POST -> GET returns the created data).
    """

    def __init__(self, spec: NormalizedSpec):
        self.spec = spec
        self.app = FastAPI(title="AutoAPI Intelligent Mock Server")
        self.state_db: Dict[str, Dict[str, Any]] = {}  # In-memory "database": resource_name -> ID -> data
        self._setup_routes()

    def _setup_routes(self):
        # We define a catch-all route to handle dynamic routing
        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
        async def dynamic_handler(request: Request, path: str):
            method = request.method.lower()
            url_path = f"/{path}"
            
            # Find matching operation in spec
            matched_op = None
            for op in self.spec.operations:
                # Basic path prefix matching - in reality, we'd regex map path params like /users/{id}
                # For this MVP, we use naive matching
                spec_path_clean = op.path.split("/{")[0]
                if url_path.startswith(spec_path_clean) and op.method == method:
                    matched_op = op
                    break
                    
            if not matched_op:
                return Response(status_code=404, content=json.dumps({"error": "Endpoint not documented in spec."}))

            # Extract resource name from path (e.g., /users/123 -> users)
            resource = url_path.strip("/").split("/")[0]
            if resource not in self.state_db:
                self.state_db[resource] = {}

            # Handle statefully based on method
            if method in ["post", "put", "patch"]:
                try:
                    body = await request.json()
                    # Assign a mock ID if missing
                    obj_id = body.get("id", str(len(self.state_db[resource]) + 1))
                    body["id"] = obj_id
                    
                    # Store in our pseudo-database
                    self.state_db[resource][obj_id] = body
                    return body
                except Exception:
                    return Response(status_code=400, content=json.dumps({"error": "Invalid body payload."}))
                    
            elif method == "get":
                parts = url_path.strip("/").split("/")
                if len(parts) > 1:
                    # e.g., /users/123 --> return specific resource
                    obj_id = parts[1]
                    if obj_id in self.state_db[resource]:
                        return self.state_db[resource][obj_id]
                    else:
                        # Fallback to generating mock data based on schema if not found in state
                        # We use Llama3.2 to generate a context-aware mock based on the endpoint schema
                        return await self._generate_ai_mock(matched_op, obj_id)
                else:
                    # Return all stored resources as a list
                    return list(self.state_db[resource].values())
                    
            elif method == "delete":
                parts = url_path.strip("/").split("/")
                if len(parts) > 1:
                    obj_id = parts[1]
                    if obj_id in self.state_db[resource]:
                        del self.state_db[resource][obj_id]
                        return Response(status_code=204)
                return Response(status_code=404)
                
            return {"message": f"AutoAPI Mock processed {method.upper()} {url_path}"}

    async def _generate_ai_mock(self, op, obj_id: str) -> Dict[str, Any]:
        """Use Llama 3.2 to generate realistic mock data when a resource isn't in memory."""
        try:
            # Find the schema for the 200/201 response
            schema = None
            for code, resp in op.responses.items():
                if str(code).startswith("2") and "content" in resp:
                    schema = resp["content"].get("application/json", {}).get("schema")
                    break
                    
            if not schema:
                return {"id": obj_id, "mocked": True, "notice": "No response schema found"}

            llm = get_llm_text(temperature=0.3)
            prompt = f"Generate a JSON object acting as a mock response for an API endpoint '{op.method.upper()} {op.path}'. " \
                     f"The object MUST adhere to this JSON schema: {json.dumps(schema)}. " \
                     f"Ensure the 'id' field is set to '{obj_id}' if present. " \
                     f"Return ONLY the valid JSON object, no markdown blocks."

            response = llm.invoke([{"role": "user", "content": prompt}])
            response_text = response.content
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                return json.loads(response_text[start_idx:end_idx])
                
            return {"id": obj_id, "error": "AI failed to generate valid JSON"}
        except Exception as e:
            logger.warning(f"AI mock generation failed: {e}")
            return {"id": obj_id, "mock_fallback": True}

def run_intelligent_mock(spec_path: str, port: int = 8080):
    spec_raw = OpenAPILoader.load_spec(spec_path)
    normalized = SpecNormalizer.normalize(spec_raw)
    
    server = IntelligentMockServer(normalized)
    print(f"🚀 Starting AutoAPI Intelligent Mock Server on port {port}...")
    uvicorn.run(server.app, host="0.0.0.0", port=port, log_level="info")
