# ======================================================================= #
# Copyright (C) 2024 Hoverset Group.                                      #
# ======================================================================= #
import tkinter

from hoverset.data import actions
from hoverset.ui.icons import get_icon_image as icon
from hoverset.ui.menu import MenuUtils, EnableIf, LoadLater
from hoverset.util.execution import Action
from studio.feature import ComponentPane
from studio.feature.components import ClickToAddGroup
from studio.feature.stylepane import StyleGroup, AttributeGroup
from studio.i18n import _
from studio.lib import NameGenerator
from studio.lib.legacy import Menu
from studio.lib.menu import *
from studio.lib.menu import MenuItem
from studio.parsers.loader import MenuStudioAdapter
from studio.tools._base import BaseTool
from studio.ui.tree import NestedTreeView

_item_map = {
    tkinter.COMMAND: Command,
    tkinter.CHECKBUTTON: CheckButton,
    tkinter.RADIOBUTTON: RadioButton,
    tkinter.SEPARATOR: Separator,
    tkinter.CASCADE: Cascade
}


class MenuTreeView(NestedTreeView):
    class Node(NestedTreeView.Node):
        def __init__(self, parent, **config):
            super().__init__(parent, **config)
            self.item: MenuItem = config.get('item')
            self.item.node = self
            self._color = self.style.colors["secondary2"]
            self.name_pad.configure(text=self.item.name)
            self.icon_pad.configure(
                image=icon(self.item.icon, 15, 15, color=self._color)
            )
            self.editable = True
            self.strict_mode = True

        def color(self):
            return self.style.colors["secondary2"]

        def widget_modified(self, widget):
            if not isinstance(widget, MenuItem):
                return
            self.item = widget
            self.name_pad.configure(text=self.item.name)
            self.icon_pad.configure(
                image=icon(self.item.icon, 15, 15, color=self._color)
            )

    def __init__(self, menu, **kw):
        super().__init__(menu.node, **kw)
        self.menu_node = menu.node
        self.menu = menu
        self.allow_multi_select(True)

    def add(self, node):
        super().add(node)
        if self not in self.menu_node.nodes:
            self.menu_node.add(self)

    def insert(self, index=None, *nodes):
        super().insert(index, *nodes)
        if self not in self.menu_node.nodes and nodes:
            self.menu_node.add(self)

    def remove(self, node):
        super().remove(node)
        if not self.nodes:
            self.menu_node.remove(self)

    def reorder(self, reorder_data):
        for item in reorder_data:
            self.insert(reorder_data[item], item.node)


class MenuStyleGroup(StyleGroup):

    def __init__(self, master, pane, **cnf):
        self.tool = cnf.pop('tool', None)
        super().__init__(master, pane, **cnf)
        self.label = _("Menu Item")
        self.prop_keys = None
        self._prev_prop_keys = set()
        self._empty_message = _("Select menu item to see styles")

    @property
    def menu_items(self):
        return self.tool.selected_items

    def supports_widgets(self):
        if len(self.widgets) != 1:
            return False
        widget = self.widgets[0]
        if self.tool.menu != widget:
            return False
        return bool(self.menu_items)

    def can_optimize(self):
        return self.prop_keys == self._prev_prop_keys

    def compute_prop_keys(self):
        items = self.menu_items
        if not items:
            self.prop_keys = set()
        else:
            self.prop_keys = None
            # determine common configs for multi-selected items
            for item in self.menu_items:
                if self.prop_keys is None:
                    self.prop_keys = set(item.configure())
                else:
                    self.prop_keys &= set(item.configure())

    def on_widgets_change(self):
        self._prev_prop_keys = self.prop_keys
        self.compute_prop_keys()
        super(MenuStyleGroup, self).on_widgets_change()
        self.style_pane.remove_loading()

    def _get_prop(self, prop, widget):
        # not very useful to us
        return None

    def _get_key(self, widget, prop):
        # generate a key identifying the multi-selection state and prop modified
        return f"{','.join(map(lambda x: str(x._index), self.menu_items))}:{prop}"

    def _get_action_data(self, widget, prop):
        return {item: {prop: item.cget(prop)} for item in self.menu_items}

    def _apply_action(self, prop, value, widgets, data):
        data = data[0]
        for item in data:
            item.configure(data[item])
        if self.tool.menu == widgets[0]:
            self.on_widgets_change()
        self.tool.on_items_modified(data.keys())

    def _set_prop(self, prop, value, widget):
        for item in self.menu_items:
            item.configure({prop: value})
        self.tool.on_items_modified(self.menu_items)

    def get_definition(self):
        if not self.menu_items:
            return {}
        rough_definition = self.menu_items[0].properties
        if len(self.menu_items) == 1:
            # for single item no need to refine definitions any further
            return rough_definition
        resolved = {}
        for prop in self.prop_keys:
            if prop not in rough_definition:
                continue
            definition = resolved[prop] = rough_definition[prop]
            # use default for value
            definition.update(value=definition['default'])
        return resolved


class CascadeMenuStyleGroup(AttributeGroup):

    def __init__(self, master, pane, **cnf):
        self.tool = cnf.pop('tool', None)
        super().__init__(master, pane, **cnf)
        self.label = _("Cascade Menu Attributes")
        self._widgets = []

    @property
    def widgets(self):
        return self._widgets

    def supports_widgets(self):
        items = self.tool.selected_items
        if any(item.item_type != "cascade" for item in items):
            return False
        items = list(filter(lambda x: x.item_type == "cascade", items))
        self._widgets = [i.sub_menu for i in items]
        if len(super().widgets) != 1:
            return False
        widget = super().widgets[0]
        if widget != self.tool.menu:
            return False
        return isinstance(widget, Menu) and items

    def can_optimize(self):
        return False


class MenuToolX(BaseTool):
    name = 'Menu'
    icon = 'menubutton'

    def __init__(self, studio, manager):
        super().__init__(studio, manager)
        self.menu = None
        MenuStudioAdapter._tool = self
        self._component_pane: ComponentPane = self.studio.get_feature(ComponentPane)
        self.item_select = self._component_pane.register_group(
            _("Menu"), MENU_ITEMS, ClickToAddGroup, self._evaluator
        )
        self.item_select.on_select(self.on_item_add)
        studio.style_pane.add_group(
            MenuStyleGroup, tool=self
        )
        studio.style_pane.add_group(
            CascadeMenuStyleGroup, tool=self
        )

        self.generator = NameGenerator(self.studio.pref)

        self.studio.bind("<<SelectionChanged>>", self.on_select, "+")

        actions.get("STUDIO_CUT").add_listener(self.cut_items)
        actions.get("STUDIO_COPY").add_listener(self.copy_items)
        actions.get("STUDIO_DELETE").add_listener(self.remove_items)

        def acc(key):
            return {"accelerator": actions.get(key).accelerator}

        self._item_context_menu = MenuUtils.make_dynamic((
            EnableIf(
                lambda: self.selected_items,
                ("separator",),
                ("command", _("copy"), icon("copy", 18, 18), self.copy_items, {**acc("STUDIO_COPY")}),
                EnableIf(
                    lambda: self._clipboard is not None,
                    ("command", _("paste"), icon("clipboard", 18, 18), self.paste_items, {**acc("STUDIO_PASTE")}),
                ),
                ("command", _("cut"), icon("cut", 18, 18), self.cut_items, {**acc("STUDIO_CUT")}),
                ("separator",),
                ("command", _("delete"), icon("delete", 18, 18), self.remove_items, {**acc("STUDIO_DELETE")}),
                LoadLater(
                    lambda: self.selected_items[0].create_menu() if len(self.selected_items) == 1 else ()),
            ),
        ), self.studio, self.studio.style)

    @property
    def _clipboard(self):
        return self.studio.get_clipboard("menu")

    def _evaluator(self, widget):
        return isinstance(widget, Menu) and len(self.studio.selection) == 1

    def _show_item_menu(self, item):
        def show(event):
            if item not in self.selected_items:
                item.node.select()
            MenuUtils.popup(event, self._item_context_menu)
        return show

    @staticmethod
    def refresh_menu_indices(menu):
        if hasattr(menu, "_items"):
            for i, item in enumerate(menu._items):
                item._index = i

    @property
    def selected_items(self):
        if self.menu:
            return [node.item for node in self.menu._sub_tree.get()]
        return []

    def create_item(self, component=None, menu=None, item=None, sub_menu=None, silently=False):
        if menu is None:
            if item is None:
                return
            menu = item.menu

        index = len(menu._items)
        if item is None:
            name = self.generator.generate(component, None)
            item = component(menu, index, label=name)

        menu._items.append(item)
        if menu == self.menu or hasattr(menu, "_sub_tree"):
            node = menu._sub_tree
        else:
            node = menu.node

        item_node = node.add_as_node(item=item)
        MenuUtils.bind_all_context(item_node, self._show_item_menu(item))
        if isinstance(item, Cascade):
            sub_menu = Menu(self.menu, tearoff=0) if sub_menu is None else sub_menu
            sub_menu.node = sub_menu.real_node = item_node
            sub_menu._items = []
            menu.entryconfig(item.index, menu=sub_menu)
            item.sub_menu = sub_menu

        if not silently:
            config = item.get_altered_options()
            self.studio.new_action(Action(
                lambda _: self.remove_items([item], silently=True),
                lambda _: self.restore_items([item], [menu], [index], [config])
            ))
        return item

    def cut_items(self):
        if self.selected_items:
            self.copy_items()
            self.remove_items()
            return True

    def _deep_copy(self, item):
        options = item.get_altered_options()
        if 'menu' in options:
            options.pop('menu')
        if item.item_type == 'cascade':
            return (
                item.item_type,
                options,
                [self._deep_copy(i) for i in item.sub_menu._items]
            )
        return item.item_type, options, None

    def copy_items(self):
        if self.selected_items:
            data = [
                self._deep_copy(item) for item in self.selected_items
            ]
            self.studio.set_clipboard(data, self.paste_items, "menu")
            return True

    def _create_paste_items(self, items, nodes, data):
        for item_type, options, sub_items in data:
            for node in nodes:
                if isinstance(node, Menu):
                    menu = node
                else:
                    menu = node.item.sub_menu
                item = _item_map[item_type](menu, len(menu._items), **options)
                self.create_item(item=item, silently=True)
                item.node.widget_modified(item)
                if items is not None:
                    items.append(item)
                if sub_items:
                    self._create_paste_items(None, [item.node], sub_items)

    def paste_items(self, clipboard=None):
        if not self.menu:
            return
        clipboard = self._clipboard if clipboard is None else clipboard
        if not clipboard:
            return
        nodes = [i for i in self.menu._sub_tree.get() if isinstance(i.item, Cascade)]
        if not nodes:
            nodes = [self.menu]
        items = []
        self._create_paste_items(items, nodes, clipboard)

        item_data = [(item, item.menu, item._index, item.get_altered_options()) for item in items]
        self.studio.new_action(Action(
            lambda _: self.remove_items(items, silently=True),
            lambda _: self.restore_items(*zip(*item_data))
        ))

    def _deselect(self, item):
        self.menu._sub_tree.deselect(item.node)

    def remove_items(self, items=None, silently=False):
        has_selected = False
        if items is None:
            items = self.selected_items
            has_selected = bool(self.selected_items)

        # to make sure items are re-inserted in the right order later
        items = sorted(items, key=lambda x: x._index)
        menus, configs = [], []
        # store original indices of items to be removed
        indices = [item._index for item in items]
        for item in items:
            menu = item.menu
            if item not in menu._items:
                continue
            self._deselect(item)
            self.studio.designer.remove_color_data(item.properties)
            indices.append(item._index)
            configs.append(item.get_altered_options())
            menu.delete(item.index)
            menu._items.remove(item)
            MenuToolX.refresh_menu_indices(menu)
            item.node.remove()
            menus.append(menu)

        if not silently:
            self.studio.new_action(Action(
                lambda _: self.restore_items(items, menus, indices, configs),
                lambda _: self.remove_items(items, silently=True)
            ))

        # Block event propagation if there are items selected
        if has_selected:
            return True

    def restore_items(self, items, menus, indices, configs):
        unique_menus = set()
        for item, menu, index, config in zip(items, menus, indices, configs):
            item.menu = menu
            menu._items.insert(index, item)
            menu.insert(index + int(menu["tearoff"]), item.item_type, **config)
            menu.real_node.insert(index, item.node)
            unique_menus.add(menu)
            self.studio.designer.add_color_data(item.properties)

        for menu in unique_menus:
            MenuToolX.refresh_menu_indices(menu)

    def on_item_add(self, component):
        nodes = [i for i in self.menu._sub_tree.get() if isinstance(i.item, Cascade)]
        if not nodes:
            self.create_item(component, self.menu)
            return
        item_data = []
        for node in nodes:
            item = self.create_item(component, node.item.sub_menu, silently=True)
            item_data.append((item, item.menu, item._index, item.get_altered_options()))

        self.studio.new_action(Action(
            lambda _: self.remove_items(list(zip(*item_data))[0], silently=True),
            lambda _: self.restore_items(*zip(*item_data))
        ))

    def initialize(self, menu):
        menu._items = []
        menu._sub_tree = MenuTreeView(menu)
        menu.real_node = menu._sub_tree
        menu._sub_tree.on_select(self._update_selection, menu)
        menu._sub_tree.on_structure_change(self._on_tree_reorder, menu)
        menu._initialized = True

    def rebuild_tree(self, menu):
        if not menu:
            return
        size = menu.index(tkinter.END)
        if size is None:
            # menu is empty
            size = -1
        for i in range(size + 1):
            if menu.type(i) == 'tearoff':
                continue
            item = _item_map[menu.type(i)](menu, len(menu._items), create=False)
            if menu.type(i) == tkinter.CASCADE:
                sub_menu = menu.nametowidget(menu.entrycget(i, 'menu'))
                self.create_item(item=item, sub_menu=sub_menu, silently=True)
                self.rebuild_tree(sub_menu)
            else:
                self.create_item(item=item, silently=True)

    def _on_tree_reorder(self, menu):
        items = [node.item for node in menu._sub_tree.get()]
        if not items:
            return

        parent_node = items[0].node.parent_node
        if isinstance(parent_node, MenuTreeView.Node):
            dest_menu = parent_node.item.sub_menu
        else:
            dest_menu = menu

        original_data = []
        new_data = []
        for item in items:
            original_data.append((
                item, item.menu, item._index
            ))
            new_data.append((
                item, dest_menu, item.node.index()
            ))

        # insertions only work correctly with sorted indices
        original_data.sort(key=lambda x: x[2])
        new_data.sort(key=lambda x: x[2])
        self._reorder(new_data, alter_tree=False)
        self.studio.new_action(Action(
            lambda _: self._reorder(original_data),
            lambda _: self._reorder(new_data)
        ))

    def _reorder(self, reorder_data, alter_tree=True):
        # deletion needs to be done in reversed order of current indices
        items = sorted(
            [item for item, _, _ in reorder_data],
            key=lambda x: x._index, reverse=True
        )
        prev_configs = {}
        for item in items:
            prev_configs[item] = item.get_altered_options()
            item.menu.delete(item.index)
            item.menu._items.remove(item)
            MenuToolX.refresh_menu_indices(item.menu)
            if alter_tree:
                item.node.remove()

        for item, menu, index in reorder_data:
            prev_config = prev_configs[item]
            menu.insert(index + int(menu["tearoff"]), item.item_type, **prev_config)
            menu._items.insert(index, item)
            MenuToolX.refresh_menu_indices(menu)
            item.menu = menu
            if alter_tree:
                menu.real_node.insert(index, item.node)

    def _update_selection(self, menu):
        if menu != self.menu:
            self.studio.selection.set(menu)
        self.studio.style_pane.render_styles()

    def _clear_selection(self):
        for i in [node.item for node in self.menu._sub_tree.get()]:
            self.menu._sub_tree.deselect(i.node)

    def on_items_modified(self, items):
        for item in items:
            item.node.widget_modified(item)

    def on_widget_add(self, widget, parent):
        if isinstance(widget, Menu):
            self.initialize(widget)
            self.rebuild_tree(widget)

    def on_select(self, _):
        if len(self.studio.selection) == 1:
            widget = self.studio.selection[0]
        else:
            widget = None

        if self.menu == widget:
            return

        if self.menu:
            self._clear_selection()

        if isinstance(widget, Menu):
            if not getattr(widget, '_initialized', False):
                self.initialize(widget)
            self.menu = widget
        else:
            self.menu = None
