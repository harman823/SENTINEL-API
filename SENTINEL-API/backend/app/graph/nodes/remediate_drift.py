from typing import Dict, Any, List
from backend.app.graph.state import GraphState
from backend.app.core.llm import get_llm
import yaml
import copy
import logging

logger = logging.getLogger(__name__)

def remediate_drift_node(state: GraphState) -> Dict[str, Any]:
    """
    Graph node: "Drift-to-PR" feature.
    If contract drift is detected, uses Llama 3.2 to generate an auto-remediation patch.
    Falls back to a stub remediation when LLM is unavailable (instant).
    """
    try:
        drift_results = state.get("drift_results", [])
        if not drift_results:
            return {"remediation_results": []}

        spec_raw = state.get("spec_raw", {})
        remediation_results = []
        llm = get_llm(temperature=0.0)

        for drift_report in drift_results:
            endpoint = drift_report.get("endpoint")
            drifts = drift_report.get("drifts", [])
            test_id = drift_report.get("test_id")
            
            if not drifts:
                continue

            # If LLM is unavailable, generate a stub remediation
            if llm is None:
                remediation_results.append({
                    "endpoint": endpoint,
                    "test_id": test_id,
                    "status": "remediation_pending",
                    "patch_proposed": f"[{len(drifts)} drift(s) detected — enable Ollama for AI-generated patches]",
                    "message": f"Detected {len(drifts)} drifts. Start Ollama with llama3.2 for auto-remediation.",
                })
                continue

            prompt = f"""
You are an expert platform engineering AI.
The API endpoint '{endpoint}' returned results that drift from its OpenAPI specification.

Drifts found:
{yaml.dump(drifts)}

Please provide a JSON output that describes exactly what needs to be changed in the OpenAPI spec to fix this drift.
Use this format:
{{
  "action": "add_field",
  "path": "the OpenAPI schema path (e.g. paths./users.get.responses.200.content.application/json.schema.properties.new_field)",
  "value_type": "string"
}}
Return a list of these JSON change objects representing the remediation patch.
"""
            
            messages = [
                {"role": "system", "content": "You are an API contract fixing assistant. Always output a valid JSON array."},
                {"role": "user", "content": prompt}
            ]
            response = llm.invoke(messages)
            
            patch_data = response.content
            
            remediation_results.append({
                "endpoint": endpoint,
                "test_id": test_id,
                "status": "remediated_locally",
                "patch_proposed": patch_data,
                "message": f"Generated auto-remediation for {len(drifts)} drifts."
            })
            
            logger.info(f"Generated auto-remediation for drift on {endpoint}")

        return {"remediation_results": remediation_results}
        
    except Exception as e:
        logger.error(f"Remediation failed: {str(e)}")
        return {
            "remediation_results": [],
            "errors": (state.get("errors") or []) + [f"Remediation failed: {str(e)}"],
        }
