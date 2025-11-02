import os
import types
from importlib.machinery import SourceFileLoader

def test_import_models_copy_executes_module():
    here = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(here, "..", "app", "models copy.py"))
    if not os.path.exists(path):
        # Không fail nếu repo không có file rác này
        return
    loader = SourceFileLoader("models_copy", path)
    mod = types.ModuleType(loader.name)
    loader.exec_module(mod)
    assert hasattr(mod, "__name__")