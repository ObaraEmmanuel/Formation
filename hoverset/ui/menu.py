import functools
import tkinter as tk
from hoverset.ui.styles import StyleDelegator


class Manipulator:
    __slots__ = ('templates',)

    def __init__(self, *templates):
        self.templates = templates

    def manipulated(self):
        return self.templates

    def __iter__(self):
        return iter(self.manipulated())

    def __getitem__(self, item):
        return self.manipulated()[item]

    def __len__(self):
        return len(self.manipulated())


class ShowIf(Manipulator):
    __slots__ = ('predicate',)

    def __init__(self, predicate, *templates):
        super().__init__(*templates)
        self.predicate = predicate

    def manipulated(self):
        if self.predicate():
            return self.templates
        return ()


class EnableIf(Manipulator):
    __slots__ = ('predicate',)

    def __init__(self, predicate, *templates):
        super().__init__(*templates)
        self.predicate = predicate

    def manipulated(self):
        if self.predicate():
            return self.templates
        return [(*t[:-1], {'state': tk.DISABLED, **t[-1]}) if len(t) == 5 else t for t in self.templates]


class MenuUtils:
    image_cache = set()

    @classmethod
    def _make_menu(cls, templates, menu, style: StyleDelegator = None):
        # populate the menu by following the templates
        raw_templates = []
        # expand manipulators to their constituent templates
        # the manipulators will perform their given transformations first
        for t in templates:
            if isinstance(t, Manipulator):
                for sub_t in t:
                    raw_templates.append(sub_t)
            else:
                raw_templates.append(t)

        for template in raw_templates:
            if template[0] == "separator":
                config = {} if len(template) == 1 else template[1]
                menu.add_separator(**config)
            else:
                _type, label, icon, command, config = template
                # create a new config copy to prevent messing with the template
                config = dict(**config)
                if style:
                    config.update(
                        {**style.dark_context_menu_selectable} if _type in ("radiobutton", "checkbutton")
                        else {**style.dark_context_menu_item})
                    if config.get('state') == tk.DISABLED:
                        # We need to work around tkinter default disabled look if possible
                        # look which tends to render incorrectly
                        config.update(**style.dark_context_menu_disabled, state=tk.NORMAL)
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

    @classmethod
    def make_dynamic(cls, templates, parent=None, style: StyleDelegator = None, dynamic=True, **cnf):
        """
        Create a dynamic menu object under a tkinter widget parent
        :param dynamic: suppress dynamic behaviour, useful for toplevel menubar. Default is set to true
        :param style: hoverset StyleDelegator object to allow retrieval of necessary menu theme styles
        :param templates: a tuple that may contain the following:
            1. a tuples of the format (type, label, icon, command, additional_configuration={}) where type is
            either command, cascade, radiobutton, checkbutton
            2. a tuple of he format ('separator', (config: dict)) to declare a separator. The config is optional
            3. a Manipulator object
        :param parent: The parent of the menu. You will never need to set this attribute directly as it only exists
        for the purposes of recursion
        :param cnf: configuration for created menu
        :return:dynamic menu
        """
        if style:
            cnf.update(style.dark_context_menu)
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


def dynamic_menu(func):
    """
    Generate a dynamic menu from a class method
    :param func: An instance method taking one positional argument menu. This method wil be called
    every time the menu needs to be posted. Note that the menu will always be cleared before
    the method is called
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
