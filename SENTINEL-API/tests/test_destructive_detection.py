import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.spec_normalizer import SpecNormalizer
from backend.app.schemas.spec import Operation

def test_destructive_detection():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {
            "/safe": {
                "get": {"description": "Safe"}
            },
            "/unsafe": {
                "delete": {"description": "Unsafe"},
                "put": {"description": "Unsafe"},
                "patch": {"description": "Unsafe"},
                "post": {"description": "Maybe safe?"}
            }
        }
    }
    
    normalized = SpecNormalizer.normalize(spec)
    
    ops = {op.method: op for op in normalized.operations}
    
    assert ops['get'].is_destructive is False
    assert ops['delete'].is_destructive is True
    assert ops['put'].is_destructive is True
    assert ops['patch'].is_destructive is True
    assert ops['post'].is_destructive is False # By default only PUT/PATCH/DELETE
    
    print("Destructive detection test passed!")

if __name__ == "__main__":
    test_destructive_detection()
