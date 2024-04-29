import os
import logging

from hoverset.util.execution import import_path


def init_externals(studio):

    external = os.path.dirname(__file__)
    for module_path in os.listdir(external):
        if module_path.endswith(".py") and module_path != "__init__.py":
            try:
                module = import_path(os.path.join(external, module_path))
            except Exception as e:
                logging.error(f"Failed to load external module {module_path}: {e}")
                continue

            if hasattr(module, "init"):
                module.init(studio)
