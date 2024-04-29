import os
import logging

from studio.external._base import FeatureNotAvailableError

from hoverset.util.execution import import_path


def init_externals(studio):

    external = os.path.dirname(__file__)
    for module_path in os.listdir(external):
        if module_path.endswith(".py") and not module_path.startswith("_"):
            try:
                module = import_path(os.path.join(external, module_path))
                if hasattr(module, "init"):
                    module.init(studio)
            except FeatureNotAvailableError:
                # feature is probably not installed
                pass
            except Exception as e:
                logging.error(f"Failed to load external module {module_path}: {e}")
                continue
