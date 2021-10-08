"""
Menu editor for the studio widgets including menu functionality
"""
# ======================================================================= #
# Copyright (C) 2020 Hoverset Group.                                      #
# ======================================================================= #

import functools
import tkinter as tk

from hoverset.ui.icons import get_icon_image
from hoverset.ui.widgets import PanedWindow, Frame, MenuButton, Button, ScrolledFrame, Label
from hoverset.ui.menu import EnableIf
from studio.lib.properties import PROPERTY_TABLE, get_properties
from studio.lib.menu import menu_config, MENU_PROPERTY_TABLE, MENU_PROPERTIES
from studio.ui.editors import StyleItem, get_display_name
from studio.ui.tree import MalleableTreeView
from studio.ui.widgets import CollapseFrame
from studio.tools._base import BaseToolWindow, BaseTool
from studio.preferences import Preferences


class MenuTree(MalleableTreeView):
    class Node(MalleableTreeView.Node):
        _type_def = {
            tk.CASCADE: ("menubutton",),
            tk.COMMAND: ("play",),
            tk.CHECKBUTTON: ("checkbutton",),
            tk.SEPARATOR: ("division",),
            tk.RADIOBUTTON: ("radiobutton",),
        }

        def __init__(self, tree, **config):
            super().__init__(tree, **config)
            self._menu = config.get("menu")
            self.name_pad.config(text=config.get("label"))
            icon = self._type_def.get(config.get("type"))[0]
            self.icon_pad.configure(image=get_icon_image(icon, 14, 14))
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
            return menu_config(self._menu, self.get_index(), key)

        def get_altered_options(self):
            keys = menu_config(self._menu, self.get_index())
            return {key: keys[key][-1] for key in keys if keys[key][-1] != keys[key][-2]}

        def get_options(self):
            keys = menu_config(self._menu, self.get_index())
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
            for node in nodes:
                # cache previous config which may be unobtainable after insert
                node._prev_options = node.get_altered_options()
            # get the nodes that have been inserted whether cloned or otherwise
            nodes = super().insert(index, *nodes)
            index = len(self.nodes) if index is None else index
            for i, node in enumerate(nodes, index):
                node._menu = self.sub_menu
                self.sub_menu.insert(i, node.type)
                # apply node properties from backup
                menu_config(self.sub_menu, i, **node._prev_options)

        def clone(self, parent):
            # This values may have changed so update them
            # Index config should be updated first
            self.configuration.update({
                "index": self.get_index(),
                "menu": self._menu,
                "sub_menu": self.sub_menu
            })
            # clone using updated config
            node = self.__class__(parent, **self.configuration)
            node.parent_node = self.parent_node
            node.label = self.label
            node._sub_menu = self.sub_menu
            # store previous menu options needed when inserting to new menu
            node._prev_options = self.get_altered_options()
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
        for node in nodes:
            # cache previous config which may be unobtainable after insert
            node._prev_options = node.get_altered_options()
        nodes = super().insert(index, *nodes)
        index = len(self.nodes) if index is None else index
        for i, node in enumerate(nodes, index):
            node._menu = self._menu
            self._menu.insert(i, node.type)
            menu_config(self._menu, i, **node._prev_options)


class MenuEditor(BaseToolWindow):
    # TODO Add context menu for nodes
    # TODO Add style search
    # TODO Handle widget change from the studio main control
    _MESSAGE_EDITOR_EMPTY = "No item selected"

    def __init__(self, master, widget, menu=None):
        super().__init__(master, widget)
        self.title(f'Edit menu for {widget.id}')
        if not isinstance(menu, tk.Menu):
            menu = tk.Menu(widget, tearoff=False)
            widget.configure(menu=menu)
        self._base_menu = menu
        self._tool_bar = Frame(self, **self.style.surface, **self.style.highlight_dim, height=30)
        self._tool_bar.pack(side="top", fill="x")
        self._tool_bar.pack_propagate(False)
        self._pane = PanedWindow(self, **self.style.pane_horizontal)
        self._tree = MenuTree(self._pane, widget, menu)
        self._tree.allow_multi_select(True)
        self._tree.on_select(self._refresh_styles)
        self._tree.on_structure_change(self._refresh_styles)
        self._prefs = Preferences.acquire()
        self._prefs.add_listener(
            "designer::descriptive_names",
            self._update_display_names
        )

        self._editor_pane = ScrolledFrame(self._pane)
        self._editor_pane_cover = Label(self._editor_pane, **self.style.text_passive)
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

        self._add = MenuButton(self._tool_bar, **self.style.button)
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
            self._add, title="Add menu item")
        menu_types.configure(tearoff=True)
        self._add.config(menu=menu_types)
        self._delete_btn = Button(self._tool_bar, image=get_icon_image("delete", 15, 15), **self.style.button,
                                  width=25,
                                  height=25)
        self._delete_btn.pack(side="left")
        self._delete_btn.on_click(self._delete)

        self._preview_btn = Button(self._tool_bar, image=get_icon_image("play", 15, 15), **self.style.button,
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
        ref = dict(PROPERTY_TABLE)
        ref.update(MENU_PROPERTY_TABLE)
        for prop in MENU_PROPERTIES:
            if not ref.get(prop):
                continue
            definition = dict(ref.get(prop))
            definition['name'] = prop
            self._add_item(StyleItem(self._menu_item_styles, definition, self._on_item_change))
        menu_prop = get_properties(self._base_menu)
        for key in menu_prop:
            definition = menu_prop[key]
            self._add_menu_item(StyleItem(self._menu_styles, definition, self._on_menu_item_change))

    def _on_item_change(self, prop, value):
        # Called when the style of a menu item changes
        for node in self._tree.get():
            menu_config(node._menu, node.get_index(), **{prop: value})
            # For changes in label we need to change the label on the node as well node
            node.label = node._menu.entrycget(node.get_index(), 'label')

    def _on_menu_item_change(self, prop, value):
        nodes = self._tree.get()
        menus = {node._menu for node in nodes}
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

    def _update_display_names(self, _):
        key = "display_name" if self._prefs.get("designer::descriptive_names") else "name"
        for style_item in tuple(self._style_item_ref.values()) + tuple(self._menu_style_ref.values()):
            style_item.set_label(style_item.definition[key])

    def _preview(self, *_):
        self.widget.event_generate("<Button-1>")

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


class MenuTool(BaseTool):
    _deleted = {}
    name = 'Menu'
    icon = 'menubutton'

    def close_editors(self):
        MenuEditor.close_all()

    def edit(self, widget):
        MenuEditor.acquire(widget.winfo_toplevel(), widget, widget.nametowidget(widget.cget("menu")))

    def remove(self, widget):
        # store menu for restoration
        self._deleted[widget] = widget.nametowidget(widget.cget("menu"))
        widget.configure(menu='')

    def restore(self, widget):
        if widget in self._deleted:
            widget.configure(menu=self._deleted.get(widget))
            self._deleted.pop(widget)

    def supports(self, widget):
        if widget is None:
            return widget
        return 'menu' in widget.keys()

    def get_menu(self, studio):
        icon = get_icon_image
        return (
            ('command', 'Edit', icon('edit', 14, 14), lambda: self.edit(studio.selected), {}),
            EnableIf(
                lambda: studio.selected and studio.selected['menu'] != '',
                ('command', 'Remove', icon('delete', 14, 14), lambda: self.remove(studio.selected), {})),
            EnableIf(
                lambda: studio.selected and studio.selected in self._deleted,
                ('command', 'Restore', icon('undo', 14, 14), lambda: self.restore(studio.selected), {})),
            EnableIf(
                lambda: MenuEditor._tool_map,
                ('command', 'Close all editors', icon('close', 14, 14), self.close_editors, {}))
        )
