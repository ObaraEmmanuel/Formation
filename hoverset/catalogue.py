"""
The catalogue is responsible for collecting apps and mapping out their main attributes for use in the
main app SYSTEM. It automatically scans the apps module and creates a classification
"""

import os
import importlib
import collections


app_catalogue = collections.defaultdict(set)


def _remove_extension(file):
    return file.split(".")[0]


for module in os.scandir("apps"):
    if module.name in ["__pycache__", "__init__.py"]:
        continue
    spec = None
    try:
        import_path = module.name + ".app" if module.is_dir() else _remove_extension(module.name)
        import_path = "hoverset.apps.{}".format(import_path)
        app = importlib.import_module(import_path).App
        app_catalogue[app.CATEGORY].add(app)
    except ModuleNotFoundError:
        pass
