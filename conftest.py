from pathlib import Path
import sys


workspace_root = Path(__file__).resolve().parent
for relative_path in (
    "source/goal-enforcement/tests",
    "source/goal-enforcement/scripts",
):
    module_directory = str((workspace_root / relative_path).resolve())
    if module_directory not in sys.path:
        sys.path.insert(0, module_directory)
