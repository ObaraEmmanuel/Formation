import functools
import tkinter as tk

from hoverset.data.actions import Routine
from hoverset.platform import platform_is, LINUX
from hoverset.ui.styles import StyleDelegator


class Manipulator:
    """
    Enables simplification of creation of dynamic menus allowing menu
    items to be easily manipulated at runtime
    """
    __slots__ = ('templates',)

    def __init__(self, *templates):
        self.templates = templates

    def manipulated(self):
        """
        Generate templates to be rendered when menu is displayed

        :return: manipulated templates menu
        """
        return self.templates

    def __iter__(self):
        return iter(self.manipulated())

    def __getitem__(self, item):
        return self.manipulated()[item]

    def __len__(self):
        return len(self.manipulated())


class ShowIf(Manipulator):
    """
    Builtin manipulator that displays a set of menu items only if a
    certain condition is met at runtime
    """
    __slots__ = ('predicate',)

    def __init__(self, predicate, *templates):
        super().__init__(*templates)
        self.predicate = predicate

    def manipulated(self):
        if self.predicate():
            return self.templates
        return ()


class EnableIf(Manipulator):
    """
    Built in manipulator that displays only a set of menu items if a
    condition is met at runtime. If condition is nt met, the menu items
    are displayed but are disabled
    """
    __slots__ = ('predicate',)

    def __init__(self, predicate, *templates):
        super().__init__(*templates)
        self.predicate = predicate

    def manipulated(self):
        if self.predicate():
            return self.templates
        return [(*t[:-1], {'state': tk.DISABLED, **t[-1]}) if len(t) == 5 else t for t in self.templates]


class LoadLater(Manipulator):
    """
    A built in manipulator that generates templates at runtime using a
    loader function passed in its constructor
    """
    __slots__ = ('loader',)

    def __init__(self, loader):
        super().__init__()
        self.loader = loader

    def manipulated(self):
        return () or self.loader()


class MenuUtils:
    image_cache = set()

    @classmethod
    def expand_template(cls, template):
        raw_templates = []
        # recursively expand manipulators
        if isinstance(template, Manipulator):
            for sub_t in template:
                raw_templates.extend(cls.expand_template(sub_t))
        else:
            raw_templates.append(template)
        return raw_templates

    @classmethod
    def _make_menu(cls, templates, menu, style: StyleDelegator = None):
        # populate the menu by following the templates
        raw_templates = []
        # expand any manipulators to their constituent templates
        # the manipulators will perform their internal transformations first
        for t in templates:
            raw_templates.extend(cls.expand_template(t))
        prev = None
        template_count = len(raw_templates)
        for i, template in enumerate(raw_templates):
            # suppress continuous, trailing and leading separators on the fly
            if template[0] == "separator" and prev != 'separator' and prev is not None and (i + 1) < template_count:
                config = {} if len(template) == 1 else template[1]
                menu.add_separator(**config)
            elif template[0] != "separator":
                _type, label, icon, command, config = template
                # create a new config copy to prevent messing with the template
                config = dict(**config)
                if isinstance(command, Routine):
                    config['accelerator'] = command.accelerator
                    command = command.invoke
                if style:
                    config.update(
                        {**style.context_menu_selectable} if _type in ("radiobutton", "checkbutton")
                        else {**style.context_menu_item})
                    if config.get('state') == tk.DISABLED:
                        # We need to work around tkinter default disabled look if possible
                        # look which tends to render incorrectly
                        config.update(**style.context_menu_disabled, state=tk.NORMAL)
                        command = None
                        # block the menu as well
                        if 'menu' in config:
                            config['menu'] = None
                cls.image_cache.add(icon)
                if template[0] == "cascade":
                    # Create cascade menu recursively
                    # the menu should be dynamic as well
                    if config.get('menu') is None:
                        pass
                    elif not isinstance(config.get('menu'), tk.Menu):
                        config["menu"] = cls.make_dynamic(config.get("menu"), menu, style)
                    menu.add_cascade(label=label, image=icon, command=command, compound='left', **config)
                    cls.image_cache.add(icon)
                else:
                    menu.add(_type, label=label, image=icon, command=command, compound='left', **config)
            prev = template[0]

    @classmethod
    def make_dynamic(cls, templates, parent=None, style: StyleDelegator = None, dynamic=True, **cnf):
        """
        Create a dynamic menu object under a tkinter widget parent

        :param dynamic: suppress dynamic behaviour, useful for toplevel
          menubar. Default is set to true
        :param style: hoverset StyleDelegator object to allow retrieval of
          necessary menu theme styles
        :param templates: a tuple that may contain the following

          1. a tuples of the format
             (type, label, icon, command, additional_config)
             where type is either ``command, cascade, radiobutton, checkbutton``
             and additional_config is a dict containing menu item configuration
          2. a tuple of he format ('separator', additional_config) to
             declare a separator. The additional_config is optional
          3. a :class:`Hoverset.ui.menu.Manipulator` object.

        :param parent: The parent of the menu. You will never need to set
          this attribute directly as it only exists for the purposes of
          recursion
        :param cnf: configuration for created menu
        :return: dynamic menu

        """
        if style:
            cnf.update(style.context_menu)
        menu = tk.Menu(parent, **cnf)

        def on_post():
            # clear former contents of menu to allow _make_menu to populate it afresh
            menu.delete(0, tk.END)
            cls._make_menu(templates, menu, style)

        if dynamic:
            # set postcommand only if dynamic behaviour is not suppressed
            menu.config(postcommand=on_post)
        else:
            # otherwise just populate menu on creation
            cls._make_menu(templates, menu, style)
        return menu

    @classmethod
    def popup(cls, event, menu):
        """
        Display context menu based on a right click event

        :param event: tk event object
        :param menu: tk menu to be displayed
        :return: None
        """
        try:
            menu.post(event.x_root, event.y_root)
            if platform_is(LINUX):
                menu.focus_set()
                menu.bind("<FocusOut>", lambda e: menu.unpost())
        except tk.TclError:
            pass
        finally:
            menu.grab_release()


def dynamic_menu(func):
    """
    Generate a dynamic menu from a class method

    :param func: An instance method taking one positional argument menu.
      This method wil be called every time the menu needs to be posted.
      Note that the menu will always be cleared before the method is called
    :return: the wrapped method returns a dynamic menu
    """

    @functools.wraps(func)
    def populate(self, menu=None):
        if menu is None:
            # menu doesn't exist so create one
            menu = tk.Menu()
            # call postcommand
            menu['postcommand'] = lambda: populate(self, menu)
        # clear the menu
        menu.delete(0, tk.END)
        func(self, menu)
        return menu

    return populate
