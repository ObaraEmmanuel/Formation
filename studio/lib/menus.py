"""
Menu editor for the studio widgets including menu functionality
"""
# ======================================================================= #
# Copyright (C) 2020 Hoverset Group.                                      #
# ======================================================================= #

import functools
import logging
import tkinter as tk

from hoverset.data.images import load_tk_image
from hoverset.ui.icons import get_icon_image, get_icon
from hoverset.ui.widgets import Window, PanedWindow, Frame, MenuButton, Button, ScrolledFrame, Label
from studio.lib.properties import PROPERTY_TABLE, get_properties
from studio.ui.editors import StyleItem
from studio.ui.tree import MalleableTree
from studio.ui.widgets import CollapseFrame
import studio.feature.variable_manager as var_manager


class _ImageIntercept:
    _image_lookup = {}
    _image_cache = set()
    __slots__ = ()

    @classmethod
    def set(cls, menu, index, value, prop='image'):
        try:
            image = load_tk_image(value)
        except Exception:
            logging.error("could not open image at {}".format(value))
            return
        # store the image string name in the lookup along with its path
        cls._image_lookup[str(image)] = value
        # add to cache to protect image from garbage collection
        cls._image_cache.add(image)
        menu.entryconfigure(index, **{prop: image})

    @classmethod
    def get(cls, menu, index, prop='image'):
        return cls._image_lookup.get(menu.entrycget(index, prop), '')


class _VariableIntercept:
    __slots__ = []

    @staticmethod
    def set(menu, index, value, prop):
        if isinstance(value, tk.Variable):
            menu.entryconfigure(index, **{prop: value})
        else:
            variable = var_manager.VariablePane.get_instance().lookup(value)
            if isinstance(variable, var_manager.VariableItem):
                menu.entryconfigure(index, **{prop: variable.var})
            else:
                logging.debug(f'variable {value} not found')

    @staticmethod
    def get(menu, index, prop):
        return str(var_manager.VariablePane.get_instance().lookup(menu.entrycget(index, prop)))


_MENU_SPECIFIC_DEFINITION = {
    "hidemargin": {
        "name": "hidemargin",
        "display_name": "hide margin",
        "type": "boolean",
    },
    "columnbreak": {
        "display_name": "column break",
        "type": "boolean",
    },
    "selectcolor": {
        "display_name": "select color",
        "type": "color",
    },
    "value": {
        "display_name": "value",
        "type": "text",
    },
    "accelerator": {
        "display_name": "accelerator",
        "type": "text",
    }
}

_ALL_PROPERTIES = (
    'compound', 'image', 'columnbreak', 'menu', 'label', 'foreground', 'accelerator', 'command', 'variable',
    'selectimage', 'underline', 'onvalue', 'activebackground', 'indicatoron', 'offvalue', 'value', 'background',
    'bitmap', 'activeforeground', 'hidemargin', 'font', 'selectcolor', 'state',
)


class MenuTree(MalleableTree):
    _intercepts = {
        "image": _ImageIntercept,
        "selectimage": _ImageIntercept,
        "variable": _VariableIntercept
    }

    class Node(MalleableTree.Node):
        _type_def = {
            tk.CASCADE: ("menubutton",),
            tk.COMMAND: ("play",),
            tk.CHECKBUTTON: ("checkbutton",),
            tk.SEPARATOR: ("division",),
            tk.RADIOBUTTON: ("radiobutton",),
        }

        def __init__(self, master=None, **config):
            super().__init__(master, **config)
            self._menu = config.get("menu")
            self.name_pad.config(text=config.get("label"))
            self.icon_pad.config(text=get_icon(self._type_def.get(config.get("type"))[0]))
            self.editable = True
            self.type = config.get("type")
            if config.get("type") == tk.CASCADE:
                self.is_terminal = False
                menu = config.get("sub_menu") if config.get("sub_menu") else tk.Menu(self.tree._menu, tearoff=False)
                self._sub_menu = menu
                self._menu.entryconfigure(config.get("index", tk.END), menu=self._sub_menu)
            else:
                self.is_terminal = True
                self._sub_menu = self._menu

        @property
        def label(self):
            return self.name_pad["text"]

        @label.setter
        def label(self, value):
            self.name_pad.config(text=value)

        @property
        def _type(self):
            return self._menu.type(self.get_index())

        def get_option(self, key):
            return MenuTree.menu_config(self._menu, self.get_index(), key)

        def get_altered_options(self):
            keys = MenuTree.menu_config(self._menu, self.get_index())
            return {key: keys[key][-1] for key in keys if keys[key][-1] != keys[key][-2]}

        def get_options(self):
            keys = MenuTree.menu_config(self._menu, self.get_index())
            return {key: keys[key][-1] for key in keys}

        def get_index(self):
            # tear off shifts menu item index down by one
            tear_off = int(self._menu["tearoff"])
            return self.parent_node.nodes.index(self) + tear_off

        def remove(self, node=None):
            if node and node in self.nodes:
                self.sub_menu.delete(node.get_index())
            super().remove(node)

        def add_menu_item(self, **kw):
            return self.add_as_node(menu=self._sub_menu, **kw)

        @property
        def sub_menu(self):
            return self._sub_menu

        @sub_menu.setter
        def sub_menu(self, menu):
            self._sub_menu = menu
            self._menu.entryconfigure(self.get_index(), menu=menu)

        def insert(self, index=None, *nodes):
            # create a backup of node properties in case cloning takes place
            properties = [node.get_altered_options() for node in nodes]
            # get the nodes that have actually been inserted whether cloned or otherwise
            nodes = super().insert(index, *nodes)
            index = len(self.nodes) if index is None else index
            for i, node in enumerate(nodes):
                node._menu = self.sub_menu
                # apply node properties from backup
                try:
                    self.sub_menu.insert(index, node.type)
                    MenuTree.menu_config(self.sub_menu, self.get_index(), **properties[i])
                except tk.TclError:
                    breakpoint()
                finally:
                    index += 1

        def clone(self, parent):
            # This values may have changed so update them
            self.configuration['index'] = self.get_index()  # Index config should be updated first
            self.configuration['menu'] = self._menu
            self.configuration['sub_menu'] = self.sub_menu
            # clone using updated config
            node = self.__class__(parent, **self.configuration)
            node.parent_node = self.parent_node
            node.label = self.label
            node._sub_menu = self.sub_menu
            for sub_node in self.nodes:
                # if node is a parent, clone sub-nodes recursively
                sub_node_clone = sub_node.clone(parent)
                node.add(sub_node_clone)
            return node

    def __init__(self, master, widget, menu):
        super().__init__(master)
        self._menu = menu
        self._sub_menu = menu
        self._widget = widget

    def add_menu_item(self, **kw):
        return self.add_as_node(menu=self._menu, **kw)

    def remove(self, node):
        if node in self.nodes:
            node._menu.delete(node.get_index())
            super().remove(node)

    def insert(self, index=None, *nodes):
        properties = [node.get_altered_options() for node in nodes]
        nodes = super().insert(index, *nodes)
        index = len(self.nodes) if index is None else index
        for i, node in enumerate(nodes):
            node._menu = self._menu
            self._menu.insert(index, node.type)
            MenuTree.menu_config(self._menu, index, **properties[i])
            index += 1

    @classmethod
    def menu_config(cls, menu, index, key=None, **kw):
        if not kw:
            if key in cls._intercepts:
                return cls._intercepts.get(key).get(menu, index, key)
            elif key is not None:
                return menu.entrycget(index, key)

            config = menu.entryconfigure(index)
            for prop in config:
                if prop in cls._intercepts:
                    value = cls._intercepts.get(prop).get(menu, index, prop)
                    config[prop] = (*config[prop][:-1], value)
            return config
        else:
            for prop in kw:
                if prop in cls._intercepts:
                    cls._intercepts.get(prop).set(menu, index, kw[prop], prop)
                else:
                    menu.entryconfigure(index, **{prop: kw[prop]})


class MenuEditor(Window):
    # TODO Add context menu for nodes
    # TODO Add style search
    # TODO Extend menu editor to other menu widgets
    # TODO Handle widget change from the studio main control
    _MESSAGE_EDITOR_EMPTY = "No item selected"
    _active_editors = {}

    def __init__(self, master, widget, menu=None):
        super().__init__(master)
        self._widget = widget
        MenuEditor._active_editors[widget] = self
        self.on_close(self.release)
        self.transient(master)
        self.title(f'Edit menu for {widget.id}')
        if not isinstance(menu, tk.Menu):
            menu = tk.Menu(widget, tearoff=False)
            widget["menu"] = menu
        print(menu.__class__)
        self._base_menu = menu
        self.config(**self.style.dark)
        self._tool_bar = Frame(self, **self.style.dark, **self.style.dark_highlight_dim, height=30)
        self._tool_bar.pack(side="top", fill="x")
        self._tool_bar.pack_propagate(False)
        self._pane = PanedWindow(self, **self.style.dark_pane_horizontal)
        self._tree = MenuTree(self._pane, widget, menu)
        self._tree.allow_multi_select(True)
        self._tree.on_select(self._refresh_styles)
        self._tree.on_structure_change(self._refresh_styles)

        self._editor_pane = ScrolledFrame(self._pane)
        self._editor_pane_cover = Label(self._editor_pane, **self.style.dark_text_passive)
        self._editor_pane.pack(side="top", fill="both", expand=True)
        self._menu_item_styles = CollapseFrame(self._editor_pane.body)
        self._menu_item_styles.pack(side="top", fill="x", pady=4)
        self._menu_item_styles.label = "Menu Item attributes"
        self._menu_styles = CollapseFrame(self._editor_pane.body)
        self._menu_styles.pack(side="top", fill="x", pady=4)
        self._menu_styles.label = "Menu attributes"
        self._style_item_ref = {}
        self._menu_style_ref = {}
        self._prev_selection = None

        self._add = MenuButton(self._tool_bar, **self.style.dark_button)
        self._add.pack(side="left")
        self._add.configure(image=get_icon_image("add", 15, 15))
        _types = MenuTree.Node._type_def
        menu_types = self._tool_bar.make_menu(
            [(
                tk.COMMAND,
                i.title(),
                get_icon_image(_types[i][0], 14, 14),
                functools.partial(self.add_item, i), {}
            ) for i in _types],
            self._add)
        menu_types.configure(tearoff=True)
        self._add.config(menu=menu_types)
        self._delete_btn = Button(self._tool_bar, image=get_icon_image("delete", 15, 15), **self.style.dark_button,
                                  width=25,
                                  height=25)
        self._delete_btn.pack(side="left")
        self._delete_btn.on_click(self._delete)

        self._preview_btn = Button(self._tool_bar, image=get_icon_image("play", 15, 15), **self.style.dark_button,
                                   width=25, height=25)
        self._preview_btn.pack(side="left")
        self._preview_btn.on_click(self._preview)

        self._pane.pack(side="top", fill="both", expand=True)
        self._pane.add(self._tree, minsize=350, sticky='nswe', width=350, height=500)
        self._pane.add(self._editor_pane, minsize=320, sticky='nswe', width=320, height=500)
        self.load_menu(menu, self._tree)
        self._show_editor_message(self._MESSAGE_EDITOR_EMPTY)
        self.enable_centering()
        self.focus_set()
        self._load_all_properties()

    @classmethod
    def acquire(cls, master, widget, menu=None):
        """
        To avoid opening multiple editors for the same widget use this
        constructor. It will either create an editor for the widget if none exists or bring
        an existing editor to focus.
        :param master: tk toplevel window
        :param widget: menu supporting widget
        :param menu: the widgets menu
        :return: a MenuEditor instance
        """
        if widget in cls._active_editors:
            cls._active_editors[widget].lift()
            cls._active_editors[widget].focus_set()
            return cls._active_editors[widget]
        return cls(master, widget, menu)

    def release(self):
        """
        Release an existing MenuEditor. This is called when destroying the
        MenuEditor to remove it from the active editors map allowing a new one to
        be spawned next time
        :return: None
        """
        MenuEditor._active_editors.pop(self._widget)
        self.destroy()

    def _show_editor_message(self, message):
        # Show an overlay message
        self._editor_pane_cover.config(text=message)
        self._editor_pane_cover.place(x=0, y=0, relwidth=1, relheight=1)

    def _clear_editor_message(self):
        self._editor_pane_cover.place_forget()

    def _show(self, item):
        item.pack(fill="x", pady=1)

    def _hide(self, item):
        item.pack_forget()

    def _add_item(self, item):
        # add a menu item style editor
        self._style_item_ref[item.name] = item
        self._show(item)

    def _add_menu_item(self, item):
        # add a parent menu style editor
        self._menu_style_ref[item.name] = item
        self._show(item)

    def _load_all_properties(self):
        # Generate all style editors that may be needed by any of the types of menu items
        # This needs to be called only once
        ref = dict(**PROPERTY_TABLE, **_MENU_SPECIFIC_DEFINITION)
        for prop in _ALL_PROPERTIES:
            if not ref.get(prop):
                continue
            definition = dict(**ref.get(prop))
            definition['name'] = prop
            self._add_item(StyleItem(self._menu_item_styles, definition, self._on_item_change))
        menu_prop = get_properties(self._base_menu)
        for key in menu_prop:
            definition = menu_prop[key]
            self._add_menu_item(StyleItem(self._menu_styles, definition, self._on_menu_item_change))

    def _on_item_change(self, prop, value):
        # Called when the style of a menu item changes
        for node in self._tree.get():
            MenuTree.menu_config(node._menu, node.get_index(), **{prop: value})
            # For changes in label we need to change the label on the node as well node
            node.label = node._menu.entrycget(node.get_index(), 'label')

    def _on_menu_item_change(self, prop, value):
        nodes = self._tree.get()
        menus = set([node._menu for node in nodes])
        for menu in menus:
            menu[prop] = value

    def _refresh_styles(self):
        # TODO Fix false value change when releasing ctrl key during multi-selecting
        # called when structure or selection changes
        nodes = self._tree.get()  # get current selection
        if not nodes:
            # if no nodes are currently selected display message
            self._show_editor_message(self._MESSAGE_EDITOR_EMPTY)
            return
        self._clear_editor_message()  # remove any messages
        # get intersection of styles for currently selected nodes
        # these will be the styles common to all the nodes selected, use sets for easy analysis
        styles = set(nodes[0].get_options().keys())
        for node in nodes:
            styles &= set(node.get_options().keys())
        # populate editors with values of the last item
        # TODO this is not the best approach, no value should be set for an option if it is not the same for all nodes
        node = nodes[-1]
        for style_item in self._style_item_ref.values():
            # styles for menu items
            if style_item.name in styles:
                self._show(style_item)
                style_item.set(node.get_option(style_item.name))
            else:
                self._hide(style_item)

        for style_item in self._menu_style_ref.values():
            # styles for the menu
            style_item.set(node._menu.cget(style_item.name))

    def _preview(self, *_):
        self._widget.event_generate("<Button-1>")

    def _delete(self, *_):
        # create a copy since the list may change during iteration
        selected = list(self._tree.get())
        for node in selected:
            self._tree.deselect(node)
            node.remove()
        self._refresh_styles()

    def add_item(self, _type):
        label = f"{_type.title()}"
        selected = self._tree.get()
        if len(selected) == 1 and selected[0].type == tk.CASCADE:
            node = selected[0]
        else:
            node = self._tree

        if _type != tk.SEPARATOR:
            node._sub_menu.add(_type, label=label)
        else:
            node._sub_menu.add(_type)
        node.add_menu_item(type=_type, label=label, index=tk.END)

    def load_menu(self, menu, node):
        # if the widget has a menu we need to populate the tree when the editor is created
        # we do this recursively to be able to capture even cascades
        # we cannot directly access all items in a menu or its size
        # but we can get the index of the last item and use that to get size and hence viable indexes
        size = menu.index(tk.END)
        if size is None:
            # menu is empty
            return
        for i in range(size + 1):
            if menu.type(i) == tk.CASCADE:
                label = menu.entrycget(i, "label")
                # get the cascades sub-menu and load it recursively
                sub = self.nametowidget(menu.entrycget(i, "menu"))
                item_node = node.add_menu_item(type=menu.type(i), label=label, index=i, sub_menu=sub)
                self.load_menu(item_node._sub_menu, item_node)
            elif menu.type(i) == tk.SEPARATOR:
                # Does not need a label, set it to the default 'separator'
                node.add_menu_item(type=menu.type(i), index=i, label='separator')
            elif menu.type(i) != 'tearoff':
                # skip any tear_off item since they cannot be directly manipulated
                label = menu.entrycget(i, "label")
                node.add_menu_item(type=menu.type(i), label=label, index=i)


def menu_options(widget):
    """
    Get the menu option for accessing the editor for a widget
    :param widget: widget with menu editor option
    :return: Hoverset menu notation
    """
    return (
        ("command", "Edit menu", None,
         lambda: MenuEditor.acquire(widget.winfo_toplevel(), widget, widget.nametowidget(widget.cget("menu"))), {}),
    )
