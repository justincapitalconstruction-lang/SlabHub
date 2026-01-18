# backend/app/schemas/__init__.py

"""
Expose all schema definitions from the parent schemas.py
so that imports like `from backend.app.schemas import SlabCreate`
work regardless of directory/file conflict.

Python prioritizes the schemas/ directory over schemas.py, so we
use importlib to explicitly load the .py file and re-export its contents.
"""

import importlib.util
from pathlib import Path

# Load schemas.py explicitly (sibling file to this package)
_schemas_file = Path(__file__).parent.parent / "schemas.py"
_spec = importlib.util.spec_from_file_location("_schemas_module", _schemas_file)
_schemas_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schemas_module)

# Re-export all public names from schemas.py
for _name in dir(_schemas_module):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_schemas_module, _name)

# Define __all__ for explicit exports
__all__ = [name for name in dir() if not name.startswith("_")]
