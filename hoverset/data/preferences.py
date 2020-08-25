import appdirs
import shelve
import os
import atexit
from collections import defaultdict
from hoverset.data.utils import make_path


class _PreferenceInstanceCreator(type):
    """
    We need to ensure only one config handler exists for a given config file
    """
    _instances = {}

    def __call__(cls, app, author, file, defaults, **kwargs):
        if (app, author, file) not in cls._instances:
            cls._instances[(app, author, file)] = super(_PreferenceInstanceCreator, cls).__call__(app, author, file,
                                                                                                  defaults, **kwargs)
        return cls._instances[(app, author, file)]


class SharedPreferences(metaclass=_PreferenceInstanceCreator):
    PATH_SEP = "::"

    def __init__(self, app, author, file, defaults):
        self._file = file
        self._app_dir = appdirs.AppDirs(app, author)
        self._listeners = defaultdict(list)

        if os.path.exists(os.path.join(self.get_dir(), "{}.dat".format(file))):
            self.data = self._get_shelve()
            self._deep_update(self.data, defaults)
        else:
            make_path(self.get_dir())
            self.data = self._get_shelve()
            self.data.update(defaults)
        atexit.register(self._release)

    def __del__(self):
        self._release()
        atexit.unregister(self._release())

    def _release(self):
        self.data.close()

    def get_dir(self):
        return self._app_dir.user_config_dir

    def _get_shelve(self):
        return shelve.open(os.path.join(self.get_dir(), self._file), writeback=True)

    def exists(self, path):
        """
        Check whether a config path exists.
        :param path: path to be checked
        :return: True if path exists in config file and False if otherwise
        """
        *dicts, prop = path.split(SharedPreferences.PATH_SEP)
        ref_dict = self.data
        for d in dicts:
            if d not in ref_dict:
                return False
            ref_dict = ref_dict[d]
        return prop in ref_dict

    def get_dict(self, dicts):
        ref_dict = self.data
        for d in dicts:
            if d not in ref_dict:
                raise ValueError("No such dictionary {}".format(d))
            ref_dict = ref_dict[d]
        return ref_dict

    def __getitem__(self, item):
        return self.get(item)

    def __setitem__(self, key, value):
        self.set(key, value)

    def get(self, path):
        """
        Return value stored at path. Use PATH_SEP to separate nested dictionaries
        for instance if
        data = {
            "theme": {
                "color":"red",
                "gradient": ["#4f5", "#555"]
                "font": {
                    "family": "calibri",
                    "size": 34,
            }
        }
        get("theme::color") returns "red"
        get("theme::font::size") returns 34
        :param path:
        :return:
        """
        *dicts, prop = path.split(SharedPreferences.PATH_SEP)
        ref_dict = self.get_dict(dicts)
        if prop in ref_dict:
            return ref_dict[prop]
        raise ValueError("No such value {}".format(prop))

    def set(self, path, value):
        """
        Set value for path. Use PATH_SEP to separate nested paths for instance
        "theme::color"
        :param path: path to value
        :param value: the value to be set to path
        :return: None
        """
        *dicts, prop = path.split(SharedPreferences.PATH_SEP)
        ref_dict = self.get_dict(dicts)
        ref_dict[prop] = value
        # call all listeners associated to path
        for listener in self._listeners.get(path, []):
            listener(value)

    def create_path(self, path):
        """
        Creates a config path and sets it to None if no value has been set
        :param path: config path to be created
        :return:
        """
        *dicts, key = path.split(SharedPreferences.PATH_SEP)
        ref_dict = self.data
        for d in dicts:
            if d not in ref_dict:
                ref_dict[d] = {}
            ref_dict = ref_dict[d]
        ref_dict[key] = ref_dict.get(key)

    def set_default(self, path, value):
        """
        Set value for path only if value has not already been set.
        Use PATH_SEP to separate nested paths for instance "theme::color"
        :param path: path to value
        :param value: the value to be set to path
        :return: None
        """
        if not self.exists(path):
            self.set(path, value)

    def append(self, path, *values):
        """
        Add value(s) to path given value at path is an iterable. Note: using this method makes the
        value at path a list
        :param path: path to iterable value
        :param values: value(s) to be appended to the iterable
        :return: None
        """
        val = [*self.get(path), *values]
        self.set(path, val)

    def remove(self, path):
        """
         remove value at path and path altogether. Use PATH_SEP to separate nested paths for instance
        "theme::color"
        :param path:
        :return:
        """
        *dicts, prop = path.split(SharedPreferences.PATH_SEP)
        ref_dict = self.get_dict(dicts)
        if prop in ref_dict:
            del ref_dict[prop]
        else:
            raise ValueError("No such value {}".format(prop))

    def add_listener(self, path, callback, *args, **kwargs):
        """
        Add a callback listener called when value at given path changes
        :param path: config path for instance 'studio::theme::color'
        :param callback: listener
        :param args: listener arguments
        :param kwargs: listener keyword arguments
        :return: the listener as added, use this value to remove the listener
        """
        if not self.exists(path):
            raise ValueError("{} does not exists".format(path))

        def func(x):
            callback(x, *args, **kwargs)

        self._listeners[path].append(func)
        return func

    def remove_listeners(self, path=None, callback=None):
        """
        Remove all, path specific or callback specific listeners. If path or callback
        to be removed are not found it is ignored silently
        :param path: config path for instance 'studio::theme::color'
        :param callback: the listener as returned by add_listener
        :return:
        """
        if path is None:
            self._listeners.clear()
        if path in self._listeners:
            if callback is None:
                self._listeners[path].clear()
            elif callback in self._listeners[path]:
                self._listeners[path].remove(callback)

    def _deep_update(self, update, source):
        for key in source:
            if isinstance(source[key], dict) and key in update:
                self._deep_update(update[key], source[key])
            else:
                if key in update:
                    continue
                update[key] = source[key]

    def update_defaults(self, path, defaults):
        self._deep_update(self.get(path), defaults)
