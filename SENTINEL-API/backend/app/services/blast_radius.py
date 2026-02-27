import logging
from typing import Dict, Any, List
from backend.app.schemas.spec import NormalizedSpec

logger = logging.getLogger(__name__)

class BlastRadiusService:
    """
    Feature 6: API 'Blast Radius' & Dependency Graphing.
    Analyzes the OpenAPI spec and creates a relationship graph tracing exactly
    which schemas are used by which endpoints.
    """

    @staticmethod
    def compute(spec: NormalizedSpec) -> Dict[str, Any]:
        """
        Builds a basic Dependency Graph:
        Nodes:
          - Operation (Endpoint)
          - Schema Definition
        Edges:
          - Operation -> Schema (Uses)
          - Schema -> Schema (References)
        """
        nodes = []
        edges = []
        schema_usage: Dict[str, List[str]] = {} # schema_name -> list of endpoints
        
        try:
            # 1. Add schema nodes
            components = getattr(spec, "components", {}) or {}
            schemas = components.get("schemas", {})
            for schema_name in schemas.keys():
                nodes.append({"id": f"schema_{schema_name}", "label": schema_name, "type": "schema"})
                schema_usage[schema_name] = []
                
            # 2. Add endpoint nodes and track references
            for op in spec.operations:
                op_id = f"{op.method.upper()} {op.path}"
                nodes.append({"id": f"op_{op_id}", "label": op_id, "type": "endpoint"})
                
                # Naive reference extraction: dump operation to string and look for '#/components/schemas/X'
                op_str = str(op.model_dump() if hasattr(op, 'model_dump') else op)
                for schema_name in schemas.keys():
                    if f"#/components/schemas/{schema_name}" in op_str:
                        edges.append({"source": f"op_{op_id}", "target": f"schema_{schema_name}", "type": "uses"})
                        schema_usage[schema_name].append(op_id)
                        
            # Build Blast Radius
            blast_radius_data = {}
            for schema_name, endpoints in schema_usage.items():
                blast_radius_data[schema_name] = endpoints
                
            return {
                "nodes": nodes,
                "edges": edges,
                "blast_radius_by_schema": blast_radius_data
            }
        except Exception as e:
            logger.warning(f"Failed to compute blast radius: {e}")
            return {"nodes": [], "edges": [], "blast_radius_by_schema": {}}
