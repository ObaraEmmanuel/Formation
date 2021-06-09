# ======================================================================= #
# Copyright (C) 2021 Hoverset Group.                                      #
# ======================================================================= #

from formation.formats._base import *
from formation.formats._xml import XMLFormat
from formation.formats._json import JSONFormat

FORMATS = (
    XMLFormat,
    JSONFormat
)


def get_file_types():
    return [(f.name, " ".join([f".{ext}" for ext in f.extensions])) for f in FORMATS]


def infer_format(path):
    import os
    _, extension = os.path.splitext(path)
    extension = extension.lstrip(".").lower()
    for format_ in FORMATS:
        if extension in format_.extensions:
            return format_

    raise ValueError(f"No matching formats found for extension '{extension}'")
