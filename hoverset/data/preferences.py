import appdirs
import atexit
import os
import shelve
import pickle
import glob
import logging
import tkinter as tk
from pathlib import Path
from collections import defaultdict

from hoverset.data.utils import make_path
from hoverset.data.images import get_tk_image
from hoverset.data.actions import get_routine
from hoverset.ui.dialogs import MessageDialog
from hoverset.ui.widgets import *

__all__ = (
    "SharedPreferences",
    "Component",
    "ComponentGroup",
    "PreferenceManager",
    "DependentGroup",
    "Check",
    "RadioGroup",
    "Number",
    "LabeledScale",
)


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

    class ConfigFileInUseError(IOError):

        def __init__(self, file_path):
            super().__init__(f"Config file {file_path} currently in use")

    def __init__(self, app, author, file, defaults):
        self._file = file
        self._app_dir = appdirs.AppDirs(app, author)
        self._listeners = defaultdict(list)
        files = self._get_files()

        if len(files):
            self.data = self._get_shelve()
            try:
                self._deep_update(self.data, defaults)
            except pickle.UnpicklingError:
                if len(files) > 1:
                    # we cannot tell whether the config file is really
                    # corrupted if there are multiple possibly non-pickle files
                    raise Exception("Cannot perform recovery, multiple config files found!")
                # The pickle file is corrupted
                logging.error("Config file is corrupted, attempting recovery.")
                # the cache contains the data that was recoverable
                recovered = self.data.cache
                self.data.close()
                # delete all the generated pickle files
                for f in self._get_generated_files():
                    Path(f).unlink(True)
                self.data = self._get_shelve()
                self._deep_update(self.data, defaults)
                # restore the little we could recover
                self._deep_update(self.data, recovered)

        else:
            make_path(self.get_dir())
            self.data = self._get_shelve()
            self.data.update(defaults)
        atexit.register(self._release)

    def __del__(self):
        self._release()
        atexit.unregister(self._release)

    def _release(self):
        try:
            self.data.close()
        except:
            pass

    def get_dir(self):
        return self._app_dir.user_config_dir

    def _get_files(self):
        # possible .dat extension
        files = glob.glob(os.path.join(self.get_dir(), f"{self._file}.dat"))
        # possible no extension
        files.extend(glob.glob(os.path.join(self.get_dir(), f"{self._file}")))
        return files

    def _get_generated_files(self):
        files = glob.glob(os.path.join(self.get_dir(), f'{self._file}.*'))
        files.extend(glob.glob(os.path.join(self.get_dir(), f'{self._file}')))
        return files

    def _get_shelve(self):
        path = os.path.join(self.get_dir(), self._file)
        try:
            return shelve.open(path, writeback=True)
        except IOError as e:
            if e.errno == 11:
                raise SharedPreferences.ConfigFileInUseError(path)
            else:
                raise e from None

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


class Component:

    def load(self, pref: SharedPreferences, path):
        self.pref = pref
        self.path = path
        self.set(pref.get(path))
        self._on_change = None
        self.requires_restart = False

    def _change(self, *_):
        if self._on_change:
            self._on_change()

    def commit(self):
        self.pref.set(self.path, self.get())

    def has_changes(self):
        return self.pref.get(self.path) != self.get()

    def on_change(self, callback, *args, **kwargs):
        self._on_change = lambda: callback(*args, **kwargs)

    def disable(self, flag):
        """
        Change the state of component, whether disable or enabled.
        All components must implement this method

        :param flag: set to ``True`` to disable and ``False`` to enable
        """
        raise NotImplementedError()


class ComponentGroup(Frame):

    def __init__(self, master, label):
        super().__init__(master)
        Label(
            self, **self.style.text_accent, text=label, anchor='w'
        ).pack(side="top", fill="x")
        self.config(**self.style.surface)


class DependentGroup:

    def __init__(self, group_def):
        self.controller = group_def["controller"]
        self.children = group_def["children"]
        self.allowed_values = group_def.get("allow", [])


class RadioGroup(Component, RadioButtonGroup):

    def __init__(self, master, pref, path, desc, **extra):
        super().__init__(master, extra.get('choices', ()), desc)
        self.load(pref, path)

    def disable(self, flag):
        self.disabled(flag)


class Number(Component, Frame):

    def __init__(self, master, pref, path, desc, **extra):
        super().__init__(master)
        self.config_all(**self.style.surface)
        self._label = Label(
            self, text=desc,
            **self.style.text
        )
        self._label.pack(side="left")
        self.editor = SpinBox(self, **{**self.style.spinbox, **extra})
        self.editor.pack(side="left", padx=5)
        self.load(pref, path)

    def disable(self, flag):
        self.editor.disabled(flag)
        self._label.disabled(flag)

    def set(self, value):
        self.editor.set(value)

    def get(self):
        return self.editor.get()


class LabeledScale(Component, Frame):

    def __init__(self, master, pref, path, desc, **extra):
        super().__init__(master)
        self._label = Label(self, **self.style.text, text=desc)
        self._label.pack(side="left")
        self._var = tk.IntVar()
        self._scale = Scale(self, self._var, **extra)
        self._scale.pack(side="left", padx=5)
        self._val = Label(self, **self.style.text)
        self._val.pack(side="left", padx=5)
        self.load(pref, path)
        self.config_all(**self.style.surface)
        self._scale.on_change(self._change)

    def _change(self, *_):
        super()._change(*_)
        self._val.config(text=self.get())

    def disable(self, flag):
        self._scale.disabled(flag)
        self._label.disabled(flag)

    def set(self, value):
        self._scale.set(value)
        self._val.config(text=self.get())

    def get(self):
        return self._scale.get()


class Check(Component, Checkbutton):

    def __init__(self, master, pref, path, desc, **extra):
        super().__init__(master, **extra)
        self.load(pref, path)
        self.config(text=desc, **self.style.text)
        self._var.trace("w", lambda *_: self._change())

    def disable(self, flag):
        if flag:
            self.config(state='disabled')
        else:
            self.config(state='normal')


class PreferenceManager(MessageDialog):
    class NavItem(CompoundList.BaseItem):

        def __init__(self, master, value, index, isolated=False):
            super().__init__(master, value, index, isolated)
            self.config_all(**self.style.bright)

        def render(self):
            Label(
                self, text=self.value, padx=5,
                pady=10, **self.style.text,
                anchor='w'
            ).pack(fill="x")

        def on_hover(self, *_):
            self.config_all(**self.style.surface)

        def on_hover_ended(self, *_):
            self.config_all(**self.style.bright)

    def __init__(self, master, pref, templates):
        super().__init__(master, self.render)
        self.title("Preferences")
        self.resizable(1, 1)
        self.nav.on_change(self._change_category)
        self.templates = templates
        self.pref = pref
        self.components = set()
        self._category_render = {}
        self._load_template(templates)

    def _change_category(self, new_category):
        self._load_category(new_category.value)

    def _add_component(self, parent, template) -> Component:
        if isinstance(template, DependentGroup):
            controller = self._add_component(parent, template.controller)
            dependents = []
            for child in template.children:
                dependents.append(self._add_component(parent, child))

            def set_state():
                for comp in dependents:
                    comp.disable(controller.get() not in template.allowed_values)

            controller.on_change(set_state)
            # call set state to initialize the right state
            set_state()
            return controller

        element = template["element"](
            parent, self.pref, template["path"],
            template["desc"], **template.get("extra", {}))
        element.requires_restart = template.get("requires_restart", False)
        element.on_change(self.update_state)
        element.pack(fill="x", pady=2)
        element.pack_configure(**template.get("layout", {}))
        self.components.add(element)
        return element

    def update_state(self):
        for component in self.components:
            if component.has_changes() and component.requires_restart:
                self.show_restart_prompt(True)
                break
        else:
            self.show_restart_prompt(False)

    def _load_category(self, category):
        if category in self._category_render:
            self.pref_body.clear_children()
            self._category_render[category].pack(
                fill="both", expand=True, padx=5, pady=5)
            return
        templates = self.templates[category]
        body = Frame(self.pref_body, **self.style.surface)
        for comp in templates:
            if isinstance(templates[comp], tuple):
                group = ComponentGroup(body, comp)
                for sub_comp in templates[comp]:
                    self._add_component(group, sub_comp)
                group.pack(fill="x", pady=10)
            else:
                self._add_component(body, templates[comp])

        self._category_render[category] = body
        self.pref_body.clear_children()
        body.pack(fill="both", expand=True, padx=5, pady=5)

    def _load_template(self, template):
        keys = list(template.keys())
        self.nav.set_values(keys)
        # Load the first group to begin with
        self.nav.select(0)
        self.update_state()

    def cancel(self, *_):
        self.destroy()

    def apply(self, *_):
        for component in self.components:
            if component.has_changes():
                component.commit()

    def okay(self, *_):
        self.apply()
        self.destroy()

    def apply_and_restart(self, *_):
        self.apply()
        get_routine("STUDIO_RESTART").invoke()

    def show_restart_prompt(self, flag):
        if flag:
            self._restart_label.pack(side="left")
            self._restart_button.pack(side="left", padx=20)
        else:
            self._restart_label.pack_forget()
            self._restart_button.pack_forget()

    def render(self, window):
        pane = PanedWindow(window, **self.style.surface, width=700, height=500)
        self.nav = CompoundList(pane)
        self.nav.config_all(**self.style.bright)
        self.nav.set_item_class(PreferenceManager.NavItem)
        self.pref_frame = ScrolledFrame(pane, **self.style.surface)
        self.pref_frame.fill_y = True
        self.pref_body = self.pref_frame.body
        pane.add(self.nav, width=250, minsize=250, sticky="nswe")
        pane.add(self.pref_frame, width=450, minsize=200, sticky="nswe")
        self._make_button_bar()
        warning_bar = Frame(self.bar, **self.style.surface)
        warning_bar.pack(side="left")
        self._restart_label = Label(
            warning_bar, **self.style.text, compound="left",
            image=get_tk_image("dialog_info", 20, 20),
            text="Some changes require restart"
        )
        self._restart_button = Button(
            warning_bar, **self.style.button, text="restart", height=25,
        )
        self._restart_button.configure(width=self._restart_button.measure_text("restart"))
        self._restart_button.on_click(self.apply_and_restart)
        self._restart_button.configure(**self.style.highlight_active)
        self.cancel_btn = self._add_button(text="Cancel", command=self.cancel)
        self.okay_btn = self._add_button(text="Okay", command=self.okay, focus=True)
        pane.pack(side="top", fill='both', expand=True)
