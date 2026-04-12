"""
Breaking change predictor for OpenAPI evolution.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def _operation_signature(spec: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    signatures: Dict[Tuple[str, str], Dict[str, Any]] = {}
    global_security = spec.get("security", [])

    for path, methods in (spec.get("paths", {}) or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            method_lower = str(method).lower()
            if method_lower not in HTTP_METHODS or not isinstance(op, dict):
                continue

            parameters = op.get("parameters", []) or []
            required_params = {
                str(param.get("name"))
                for param in parameters
                if isinstance(param, dict) and param.get("required")
            }

            body_schema = (
                op.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            required_body = set(body_schema.get("required", [])) if isinstance(body_schema, dict) else set()
            responses = {code for code in (op.get("responses", {}) or {}).keys() if str(code).isdigit()}
            has_security = bool(op.get("security", global_security))

            signatures[(method_lower, path)] = {
                "required_params": required_params,
                "required_body_fields": required_body,
                "responses": responses,
                "has_security": has_security,
            }

    return signatures


def _select_previous(spec_history: List[Dict[str, Any]], current_spec: Dict[str, Any]) -> Dict[str, Any]:
    if spec_history:
        return spec_history[-1]
    return current_spec


class BreakingChangePredictor:
    """Predict likely breaking changes from OpenAPI version-to-version diffs."""

    @staticmethod
    def predict(spec_history: List[Dict[str, Any]], current_spec: Dict[str, Any]) -> Dict[str, Any]:
        if not current_spec:
            return {"predictions": [], "summary": {"total": 0, "likely_breaking": 0}}

        previous = _select_previous(spec_history, current_spec)
        prev_sig = _operation_signature(previous)
        curr_sig = _operation_signature(current_spec)

        predictions: List[Dict[str, Any]] = []

        removed_ops = set(prev_sig.keys()) - set(curr_sig.keys())
        for method, path in sorted(removed_ops):
            predictions.append(
                {
                    "change_type": "operation_removed",
                    "operation": f"{method.upper()} {path}",
                    "likelihood": 0.99,
                    "is_breaking": True,
                    "reason": "Endpoint existed previously but is absent in current spec.",
                    "recommended_action": "Keep endpoint during deprecation window or release a major API version.",
                }
            )

        common_ops = set(prev_sig.keys()) & set(curr_sig.keys())
        for op_key in sorted(common_ops):
            method, path = op_key
            before = prev_sig[op_key]
            after = curr_sig[op_key]

            new_required_params = sorted(after["required_params"] - before["required_params"])
            if new_required_params:
                predictions.append(
                    {
                        "change_type": "new_required_parameter",
                        "operation": f"{method.upper()} {path}",
                        "fields": new_required_params,
                        "likelihood": 0.86,
                        "is_breaking": True,
                        "reason": "New required request parameter(s) can break existing clients.",
                        "recommended_action": "Add defaults or make parameters optional for at least one transition release.",
                    }
                )

            new_required_body = sorted(after["required_body_fields"] - before["required_body_fields"])
            if new_required_body:
                predictions.append(
                    {
                        "change_type": "new_required_body_field",
                        "operation": f"{method.upper()} {path}",
                        "fields": new_required_body,
                        "likelihood": 0.83,
                        "is_breaking": True,
                        "reason": "New required body fields can break older clients.",
                        "recommended_action": "Treat fields as optional first, then enforce in later version.",
                    }
                )

            removed_success = {
                code
                for code in before["responses"] - after["responses"]
                if 200 <= int(code) < 300
            }
            if removed_success:
                predictions.append(
                    {
                        "change_type": "success_response_removed",
                        "operation": f"{method.upper()} {path}",
                        "codes": sorted(removed_success),
                        "likelihood": 0.74,
                        "is_breaking": True,
                        "reason": "Previously documented success status code is no longer listed.",
                        "recommended_action": "Maintain prior success status mapping or version the endpoint.",
                    }
                )

            if not before["has_security"] and after["has_security"]:
                predictions.append(
                    {
                        "change_type": "security_requirement_added",
                        "operation": f"{method.upper()} {path}",
                        "likelihood": 0.76,
                        "is_breaking": True,
                        "reason": "Authentication became mandatory for an existing operation.",
                        "recommended_action": "Roll out with staged enforcement and migration guidance.",
                    }
                )

        likely_breaking = sum(1 for item in predictions if item.get("is_breaking"))
        return {
            "predictions": sorted(predictions, key=lambda item: item.get("likelihood", 0), reverse=True),
            "summary": {
                "total": len(predictions),
                "likely_breaking": likely_breaking,
                "previous_operations": len(prev_sig),
                "current_operations": len(curr_sig),
            },
        }
