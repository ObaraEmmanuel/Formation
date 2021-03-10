import errno
import sys
import os
import pkgutil
import pathlib


def get_resource_path(package, resource):
    """
    Get the path of a resource located in a :param package
    :param package: package containing resource, could be the actual package instance or a string representing the
    package for instance "foo.bar"
    :param resource: path of the resource relative to :param package
    :return:
    """
    d = os.path.dirname(sys.modules[package if isinstance(package, str) else package.__name__].__file__)
    return os.path.join(pathlib.Path(d), pathlib.Path(resource))


def make_path(path):
    """
    Create path if it does not exist. May raise OSError if creation fails
    :param path: path to create
    :return: None
    :raises OSError
    """
    # create the directory in a python 2 compatible manner
    try:
        os.makedirs(path)
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise


def get_theme_path(theme):
    if not theme.endswith(".css"):
        theme += ".css"
    # this just gets the last part of the path to allow
    # older versions using full paths to work as well
    theme = os.path.basename(theme)
    base_path = get_resource_path("hoverset.ui", "themes")
    theme_path = os.path.join(base_path, theme)
    if os.path.exists(theme_path):
        return theme_path
    return os.path.join(base_path, "default.css")


get_resource = pkgutil.get_data
