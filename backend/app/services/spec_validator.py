from typing import Dict, Any

class SpecValidator:
    @staticmethod
    def validate(spec: Dict[str, Any]) -> None:
        """
        Strictly validate the OpenAPI spec structure.
        Raises ValueError if invalid.
        """
        # 1. Check OpenAPI version
        version = spec.get('openapi', '')
        if not version.startswith('3.'):
            raise ValueError(f"Unsupported OpenAPI version: {version}. Only 3.x is supported.")

        # 2. Check required top-level fields
        if 'info' not in spec:
            raise ValueError("Missing 'info' section in spec.")
        if 'paths' not in spec:
            raise ValueError("Missing 'paths' section in spec.")

        # 3. Validate Paths (Basic check)
        paths = spec['paths']
        if not isinstance(paths, dict):
             raise ValueError("'paths' must be a dictionary.")

        # 4. Check for Empty Paths (Optional but good for strictness)
        if not paths:
            # It's technically valid to have no paths, but useful to warn or fail if strict.
            # For now, we allow it but maybe log it.
            pass

        # Additional strict checks can be added here
