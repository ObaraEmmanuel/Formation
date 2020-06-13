import sys
import os
import pkgutil


def get_resource_path(package, resource):
    """
    Get the path of a resource located in a :param package
    :param package: package containing resource, could be the actual package instance or a string representing the
    package for instance "foo.bar"
    :param resource: path of the resource relative to :param package
    :return:
    """
    d = os.path.dirname(sys.modules[package if isinstance(package, str) else package.__name__].__file__)
    return os.path.join(d, resource)


get_resource = pkgutil.get_data
