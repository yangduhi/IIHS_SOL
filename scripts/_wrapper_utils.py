from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"


def ensure_repo_root() -> None:
    for path in (str(REPO_ROOT), str(SCRIPTS_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)


def export_module(module_name: str, target_globals: dict[str, Any]) -> ModuleType:
    ensure_repo_root()
    module = importlib.import_module(module_name)
    exported_names = getattr(module, "__all__", None)
    if exported_names is None:
        exported_names = [name for name in dir(module) if not name.startswith("_")]
    for name in exported_names:
        target_globals[name] = getattr(module, name)
    target_globals.setdefault("__doc__", module.__doc__)
    return module
