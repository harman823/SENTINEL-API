import json
import yaml

spec = {
    "openapi": "3.0.0",
    "info": {
        "title": "Advanced Insights Error Testing Spec",
        "description": "An intentionally broken OpenAPI specification designed to trigger all 12 Advanced Insights error modules in SENTINEL.",
        "version": "1.0.0"
    },
    # INTENTIONAL ERROR: No global security or securitySchemes defined. 
    # This will cause the Compliance Scorecard and IaC Validator to flag missing OAuth/JWT.
    "paths": {
        "/users": {
            "get": {
                "summary": "Get all users",
                "operationId": "getUsers",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        }
                    }
                }
            },
            "post": {
                "summary": "Create a user",
                "operationId": "createUser",
                # This POST enables the Stateful Journey Generator (POST -> GET -> PUT -> DELETE)
                # It also triggers the Smart Fuzzing Agent to mutate the strict payload
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/User"}
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Created",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/User"}
                            }
                        }
                    }
                }
            }
        },
        "/users/{id}": {
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"}
                }
            ],
            "get": {
                "summary": "Get a user by ID",
                "operationId": "getUserById",
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/User"}
                            }
                        }
                    },
                    # INTENTIONAL ERROR: 404 is undocumented. 
                    # Semantic Traffic Replay and RCA will flag 404s in production as drift.
                }
            },
            "put": {
                "summary": "Update a user",
                "operationId": "updateUser",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/User"}
                        }
                    }
                },
                "responses": {
                    "200": {"description": "Updated"}
                }
            },
            "delete": {
                "summary": "Delete a user",
                "operationId": "deleteUser",
                # INTENTIONAL ERROR: Destructive operation without authorization
                "responses": {
                    "204": {"description": "Deleted"}
                }
            }
        },
        "/health": {
            "get": {
                "summary": "System Health",
                "operationId": "getHealth",
                "responses": {
                    "200": {"description": "System is healthy"}
                }
                # INTENTIONAL ERROR: Chaos Resilience Tester will inject 503s here,
                # which are not documented in the responses object.
            }
        },
        "/legacy-auth": {
            "post": {
                "summary": "Legacy Authentication",
                "operationId": "legacyAuth",
                # INTENTIONAL ERROR: Deprecated basic auth endpoint.
                # PR Remediation Bot / Gate will flag this as a security risk.
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "username": {"type": "string"},
                                    "password": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "Token"}
                }
            }
        }
    },
    "components": {
        "schemas": {
            "User": {
                # INTENTIONAL ERROR: This shared schema connects 5 different endpoints.
                # Modifying it will trigger a massive Blast Radius Explorer warning.
                "type": "object",
                "required": ["name", "email", "role"],
                "properties": {
                    "id": {"type": "integer", "readOnly": True},
                    "name": {"type": "string", "example": "John Doe"},
                    "email": {"type": "string", "format": "email", "example": "invalid-email-format"},
                    "role": {"type": "string", "enum": ["admin", "user", "guest"]}
                }
            }
        }
    }
}

# Write JSON
with open("tests/advanced_insights_test_spec.json", "w") as f:
    json.dump(spec, f, indent=2)

# Write YAML
with open("tests/advanced_insights_test_spec.yaml", "w") as f:
    yaml.dump(spec, f, sort_keys=False, default_flow_style=False)

print("Generated YAML and JSON!")
