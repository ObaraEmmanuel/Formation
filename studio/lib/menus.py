"""
Menu editor for the studio widgets including menu functionality
"""
# ======================================================================= #
# Copyright (C) 2020 Hoverset Group.                                      #
# ======================================================================= #

import functools
import tkinter as tk

from hoverset.ui.icons import get_icon_image, get_icon
from hoverset.ui.widgets import Window, PanedWindow, Frame, MenuButton, Button, ScrolledFrame, Label
from studio.lib.properties import PROPERTY_TABLE, get_properties
from studio.ui.tree import MalleableTree
from studio.ui.widgets import CollapseFrame, StyleItem

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
            return self._menu.entrycget(self.get_index(), key)

        def get_altered_options(self):
            keys = self._menu.entryconfigure(self.get_index())
            return {key: keys[key][-1] for key in keys if keys[key][-1] != keys[key][-2]}

        def get_options(self):
            keys = self._menu.entryconfigure(self.get_index())
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
            properties = {node: node.get_altered_options() for node in nodes}
            super().insert(index, *nodes)
            index = len(self.nodes) if index is None else index
            for node in nodes:
                node._menu = self.sub_menu
                try:
                    self.sub_menu.insert(index, node.type, **properties[node])
                except tk.TclError:
                    breakpoint()
                finally:
                    index += 1

    def __init__(self, master, widget, menu):
        super().__init__(master)
        self._menu = menu
        self._sub_menu = menu
        self._widget = widget

    def add_menu_item(self, **kw):
        return self.add_as_node(menu=self._menu, **kw)

    def remove(self, node):
        node._menu.delete(node.get_index())
        super().remove(node)

    def insert(self, index=None, *nodes):
        properties = {node: node.get_altered_options() for node in nodes}
        super().insert(index, *nodes)
        index = len(self.nodes) if index is None else index
        for node in nodes:
            node._menu = self._menu
            self._menu.insert(index, node.type, **properties[node])
            index += 1


class MenuEditor(Window):
    # TODO Add context menu for nodes
    # TODO Add style search
    # TODO Extend menu editor to other menu widgets
    # TODO Handle widget change from the studio main control
    _MESSAGE_EDITOR_EMPTY = "No item selected"

    def __init__(self, master, widget, menu=None):
        super().__init__(master)
        self.transient(master)
        self.title(f'Edit menu for {widget.id}')
        if not menu:
            menu = tk.Menu(widget, tearoff=False)
            widget["menu"] = menu
        else:
            menu = self.nametowidget(menu)
        self._base_menu = menu
        self._widget = widget
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

    def _show_editor_message(self, message):
        self._editor_pane_cover.config(text=message)
        self._editor_pane_cover.place(x=0, y=0, relwidth=1, relheight=1)

    def _clear_editor_message(self):
        self._editor_pane_cover.place_forget()

    def _show(self, item):
        item.pack(fill="x", pady=1)

    def _hide(self, item):
        item.pack_forget()

    def _add_item(self, item):
        self._style_item_ref[item.name] = item
        self._show(item)

    def _add_menu_item(self, item):
        self._menu_style_ref[item.name] = item
        self._show(item)

    def _load_all_properties(self):
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
        for node in self._tree.get():
            node._menu.entryconfigure(node.get_index(), **{prop: value})
            node.label = node._menu.entrycget(node.get_index(), 'label')

    def _on_menu_item_change(self, prop, value):
        nodes = self._tree.get()
        menus = set([node._menu for node in nodes])
        for menu in menus:
            menu[prop] = value

    def _refresh_styles(self):
        nodes = self._tree.get()
        if not nodes:
            self._show_editor_message(self._MESSAGE_EDITOR_EMPTY)
            return
        self._clear_editor_message()
        styles = set(nodes[0].get_options().keys())
        for node in nodes:
            styles &= set(node.get_options().keys())
        node = nodes[-1]
        for style_item in self._style_item_ref.values():
            if style_item.name in styles:
                self._show(style_item)
                style_item.set(node.get_option(style_item.name))
            else:
                self._hide(style_item)

        for style_item in self._menu_style_ref.values():
            style_item.set(node._menu.cget(style_item.name))

    def _preview(self, *_):
        self._widget.event_generate("<Button-1>")

    def _delete(self, *_):
        # create a copy since the array may change during iteration
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
        size = menu.index(tk.END)
        if size is None:
            return
        for i in range(size + 1):
            if menu.type(i) == tk.CASCADE:
                label = menu.entrycget(i, "label")
                sub = self.nametowidget(menu.entrycget(i, "menu"))
                item_node = node.add_menu_item(type=menu.type(i), label=label, index=i, sub_menu=sub)
                self.load_menu(item_node._sub_menu, item_node)
            elif menu.type(i) == tk.SEPARATOR:
                # Does not need a label
                node.add_menu_item(type=menu.type(i), index=i)
            elif menu.type(i) != 'tearoff':
                # skip any tear_off item since they cannot be manipulated
                label = menu.entrycget(i, "label")
                node.add_menu_item(type=menu.type(i), label=label, index=i)


def menu_options(widget):
    return (
        ("command", "Edit menu", None, lambda: MenuEditor(widget.winfo_toplevel(), widget, widget.cget("menu")), {}),
    )
