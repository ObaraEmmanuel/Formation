"""
Widget tree for the studio
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #
from abc import ABC
import enum

from hoverset.ui.icons import get_icon_image
from hoverset.ui.widgets import EventMask, ScrolledFrame, Label, Tree, Frame
from hoverset.ui.windows import DragWindow
from studio.ui.geometry import absolute_bounds


class InsertType(enum.IntEnum):
    INSERT_BEFORE = 0
    INSERT_INTO = 1
    INSERT_INTO_TOP = 2
    INSERT_AFTER = 3


class MalleableTree(Tree, ABC):
    """
    Abstract Sub class of Tree that allows rearrangement of Nodes which useful in repositioning components in the
    various studio features. For any tree that allows rearrangement, subclass MalleableTree.
    """
    drag_components = []  # All objects that were selected when dragging began
    drag_active = False  # Flag showing whether we are currently dragging stuff
    drag_popup = None  # The almost transparent window that shows what is being dragged
    drag_highlight = None  # The widget that currently contains the rectangular highlight
    drag_select = None  # The node where all events go when button is released ending drag
    drag_display_limit = 3  # The maximum number of items the drag popup can display
    drag_instance = None  # The current tree that is performing a drag
    drag_last_action = None  # latest drop action

    class Node(Tree.Node):
        PADDING = 0

        def __init__(self, tree, **config):
            # Master is always a TreeView object unless you tamper with the add_as_node method
            super().__init__(tree, **config)
            # If set tp False the node accepts children and vice versa
            self._is_terminal = config.get("terminal", True)
            self.strip.bind_all("<Motion>", self.drag)
            self.strip.bind_all("<Motion>", self.begin_drag, add='+')
            self.strip.config(**self.style.highlight)  # The highlight on a normal day
            self._on_structure_change = None
            # if true allows node to be dragged and repositioned
            self.editable = False
            # if true prevents node from being dragged to another tree
            self.strict_mode = False
            self.configuration = config

        def _init_binding(self):
            for i in (self.name_pad, self.icon_pad, self.expander, self.strip):
                i.bind("<ButtonRelease-1>", self.end_drag)
                i.bind("<Return>", self.select)

        def on_structure_change(self, callback, *args, **kwargs):
            self._on_structure_change = lambda: callback(*args, **kwargs)

        def _change_structure(self):
            if self._on_structure_change:
                self._on_structure_change()
            self.tree._structure_changed()

        def _edge_scroll(self, event):
            scrolled_parent = self.ancestor_first(self, ScrolledFrame)
            if scrolled_parent:
                x1, y1, x2, y2 = absolute_bounds(scrolled_parent)
                overshoot_top, overshoot_bottom = y1 - event.y_root, event.y_root - y2
                if scrolled_parent.scroll_position() != (0, 1):
                    # use -2 to allow a edge margin of about 2
                    if overshoot_top > -2:
                        scrolled_parent.yview_scroll(-1, 'units')
                    elif overshoot_bottom > -2:
                        scrolled_parent.yview_scroll(1, 'units')

        def begin_drag(self, event):
            if not self.editable or not self.tree.selected_count() \
                    or not event.state & EventMask.MOUSE_BUTTON_1:
                return
            MalleableTree.drag_active = True

        # noinspection PyProtectedMember
        def drag(self, event):
            if not self.editable or not MalleableTree.drag_active:
                return
            # only initialize if not initialized
            if not MalleableTree.drag_popup:
                MalleableTree.drag_popup = DragWindow(self.window).set_position(event.x_root, event.y_root + 20)
                MalleableTree.drag_components = self.tree._selected
                MalleableTree.drag_instance = self.tree
                count = 0
                for component in MalleableTree.drag_components:
                    # Display all items upto the drag_display_limit
                    if count == MalleableTree.drag_display_limit:
                        overflow = len(MalleableTree.drag_components) - count
                        # Display the overflow information
                        Label(MalleableTree.drag_popup,
                              text=f"and {overflow} other{'' if overflow == 1 else 's'}...", anchor='w',
                              **self.style.text).pack(side="top", fill="x")
                        break
                    Label(MalleableTree.drag_popup,
                          text=component.name, anchor='w',
                          **self.style.text).pack(side="top", fill="x")
                    count += 1
            self._edge_scroll(event)
            widget = self.containing(event.x_root, event.y_root, self)
            # The widget can be a child to Node but not necessarily a node but we need a node so
            # Resolve the node that is immediately under the cursor position by iteratively getting widget's parent
            # For the sake of performance not more than 4 iterations
            limit = 4
            while not isinstance(widget, (self.__class__, MalleableTree.ShadowNode)):
                if widget is None:
                    # This happens when someone hovers outside the current top level window
                    break
                widget = self.nametowidget(widget.winfo_parent())
                limit -= 1
                if not limit:
                    break
            tree = self.event_first(event, self.tree, MalleableTree)
            if isinstance(widget, MalleableTree.ShadowNode):
                # do nothing if we're within the shadow node
                pass
            elif isinstance(widget, self.__class__) and (not self.strict_mode or widget.tree == self.tree):
                # We can only react if we have resolved the widget to a compatible Node object
                MalleableTree.drag_last_action = widget.react(event)
                # Store the currently reacting widget so we can apply actions to it on ButtonRelease/drag_end
                MalleableTree.drag_select = widget
            elif isinstance(tree, self.tree.__class__) and (not self.strict_mode or tree == self.tree):
                # if the tree found is compatible to the current tree i.e belongs to same class or is subclass of
                # disallow incompatible trees from interacting as this may cause errors
                MalleableTree.drag_last_action = tree.react(event)
                MalleableTree.drag_select = tree
            else:
                # No viable node found on resolution so clear all highlights and indicators
                if MalleableTree.drag_select:
                    MalleableTree.drag_select.clear_indicators()
                MalleableTree.drag_select = None

            MalleableTree.drag_popup.set_position(event.x_root, event.y_root + 20)

        def end_drag(self, event):
            # Dragging is complete so we make the necessary insertions and repositions
            node = MalleableTree.drag_select
            if MalleableTree.drag_active:
                if MalleableTree.drag_select is not None:
                    action = MalleableTree.drag_last_action
                    if action == InsertType.INSERT_BEFORE:
                        node.insert_before(*MalleableTree.drag_components)
                    elif action == InsertType.INSERT_INTO:
                        node.insert(None, *MalleableTree.drag_components)
                    elif action == InsertType.INSERT_INTO_TOP:
                        node.insert(0, *MalleableTree.drag_components)
                    elif action == InsertType.INSERT_AFTER:
                        node.insert_after(*MalleableTree.drag_components)
                    # else there is no viable action to take.
                    if action in [i.value for i in InsertType]:
                        # These actions means tree structure changed
                        self._change_structure()
                # Reset all drag related attributes
                if MalleableTree.drag_popup is not None:
                    if MalleableTree.drag_select is not None:
                        MalleableTree.drag_select.clear_indicators()
                    MalleableTree.drag_popup.destroy()  # remove the drag popup window
                    MalleableTree.drag_popup = None
                    MalleableTree.drag_components = []
                    MalleableTree.drag_instance = None
                    self.clear_indicators()
                    MalleableTree.drag_highlight = None
                MalleableTree.drag_active = False
            elif event.widget != self.expander:
                self.select(event)

        def highlight(self):
            MalleableTree.drag_highlight = self
            self.strip.config(**self.style.bright_highlight)

        def react(self, event) -> int:
            # Checks, based on the cursor position whether we can insert before, into, into-top or after the node
            # Returns 0, 1, 2 or 3 respectively
            self.clear_indicators()
            # The cursor is at the top edge of the node so we can attempt to insert before it
            if event.y_root < self.strip.winfo_rooty() + 5:
                self.tree.shadow_node.show_before(self)
                return InsertType.INSERT_BEFORE
            # The cursor is at the center of the node so we can attempt a direct insert into the node
            if self.strip.winfo_rooty() + 5 < event.y_root < self.strip.winfo_rooty() + self.strip.height - 5:
                if not self._is_terminal:
                    # If node is not terminal then it does support children and consequently insertion
                    if self._expanded:
                        # insert as first child just under the expaned node
                        self.tree.shadow_node.show_before(self.nodes[0])
                        return InsertType.INSERT_INTO_TOP
                    # target node is collapsed so highlight the node and insert at the end of the node
                    self.highlight()
                    return InsertType.INSERT_INTO
            # The cursor is at the bottom edge of the node so we attempt to insert immediately after the node
            elif self._expanded:
                # If the node is expanded we would want to edge indicate at the very bottom after its last child
                if event.y_root > self.winfo_rooty() + self.height - 5:
                    self.tree.shadow_node.show_in(self)
                    return InsertType.INSERT_AFTER
            else:
                self.tree.shadow_node.show_after(self)
                return InsertType.INSERT_AFTER

        def clear_highlight(self):
            # Remove the rectangular highlight around the node
            self.strip.configure(**self.style.highlight)

        def clear_indicators(self):
            # Remove any remaining node highlights and shadow node
            if MalleableTree.drag_highlight is not None:
                MalleableTree.drag_highlight.clear_highlight()
            self.tree.shadow_node.hide()

        @property
        def is_terminal(self):
            return self._is_terminal

        @is_terminal.setter
        def is_terminal(self, value):
            self._is_terminal = value

        def insert(self, index=None, *nodes):
            # if dragging to new tree copy to new location
            # only do this during drags, i.e drag_active is True
            if MalleableTree.drag_active and MalleableTree.drag_instance != self.tree:
                # clone to new parent tree
                # the node will still be retained in the former tree
                nodes = [node.clone(self.tree) for node in nodes]
                self.clear_indicators()
            super().insert(index, *nodes)
            return nodes

        def clone(self, parent):
            #  Generic cloning that replicates node using config provided on creation
            #  Override to define attributes that may have changed
            node = self.__class__(parent, **self.configuration)
            node.parent_node = self.parent_node
            for sub_node in self.nodes:
                sub_node_clone = sub_node.clone(parent)
                node.insert(None, sub_node_clone)
            return node

    class ShadowNode(Node):

        def __init__(self, tree, **config):
            super().__init__(tree, **config)
            self.name_pad.grid_forget()
            self.icon_pad.config(**self.style.hover)
            self.area = Frame(self.strip, **self.style.bright)
            self.area.grid(row=0, column=3, sticky="nsew")
            self.area.bind("<ButtonRelease-1>", self.end_drag)

        def _get_body(self, node):
            return node.get_body() if isinstance(node, Tree) else node.body

        def _show(self, node, action=InsertType.INSERT_INTO):
            self.lift()
            self.depth = max(1, node.depth)
            self.area.config(width=self.strip.winfo_width())
            common_config = dict(fill="x")
            if action == InsertType.INSERT_AFTER:
                self.pack(in_=self._get_body(node.parent_node), after=node, **common_config)
            elif action == InsertType.INSERT_BEFORE:
                self.pack(in_=self._get_body(node.parent_node), before=node, **common_config)
            elif action == InsertType.INSERT_INTO:
                self.pack(in_=self._get_body(node), **common_config)

        def show_after(self, node):
            self._show(node, InsertType.INSERT_AFTER)

        def show_before(self, node):
            self._show(node, InsertType.INSERT_BEFORE)

        def show_in(self, node):
            self._show(node, InsertType.INSERT_INTO)

        def hide(self):
            if self.winfo_ismapped():
                self.pack_forget()

    def initialize_tree(self):
        super(MalleableTree, self).initialize_tree()
        self._on_structure_change = None
        self.is_terminal = False
        # A special node that shows where an insertion can occur
        self.shadow_node = self.__class__.ShadowNode(self)

    def on_structure_change(self, callback, *args, **kwargs):
        self._on_structure_change = lambda: callback(*args, **kwargs)

    def _structure_changed(self):
        if self._on_structure_change:
            self._on_structure_change()

    def insert(self, index=None, *nodes):
        # if dragging to new tree clone nodes to new location
        # only do this during drags, i.e drag_active is True
        if MalleableTree.drag_active and MalleableTree.drag_instance != self:
            # clone to new parent tree
            # the node will still be retained in the former tree
            nodes = [node.clone(self) for node in nodes]
            self.shadow_node.hide()
        super().insert(index, *nodes)
        # Return the nodes just in case they have been cloned and new references are required
        return nodes

    def react(self, *_):
        self.clear_indicators()
        self.shadow_node.show_in(self)
        # always perform a direct insert
        return InsertType.INSERT_INTO

    def highlight(self):
        MalleableTree.drag_highlight = self
        self.get_body().config(**self.get_body().style.bright_highlight)

    def clear_highlight(self):
        # Remove the rectangular highlight around the node
        self.get_body().configure(**self.get_body().style.highlight)

    def clear_indicators(self):
        # Remove any remaining node highlights and shadow node
        if MalleableTree.drag_highlight is not None:
            MalleableTree.drag_highlight.clear_highlight()
        self.shadow_node.hide()


class MalleableTreeView(MalleableTree, ScrolledFrame):
    """
    Malleable TreeView that allows rearrangement of Nodes which useful in
    repositioning components in the various studio features.
    For any tree view that allows rearrangement, subclass MalleableTreeView.
    """

    def __init__(self, master=None, **config):
        super().__init__(master, **config)
        self.config(**self.style.surface)
        self.initialize_tree()

    def get_body(self):
        return self.body


class NestedTreeView(MalleableTree, Frame):
    """
    Nestable malleable tree with scrolling removed

    .. note::
        Adding NestedTreeView inside a :py:class:`MalleableTree.Node` is
        not tested and may cause things to break.
    """

    class Node(MalleableTree.Node):

        EXPANDED_ICON = None
        COLLAPSED_ICON = None
        BLANK = None
        __icons_loaded = False

        def __init__(self, tree, **config):
            super().__init__(tree, **config)
            for component in (self.expander, self.icon_pad):
                component.config(**self.style.text_secondary1)
            self.name_pad.config(**self.style.text_italic)

        def color(self):
            return self.style.colors["secondary1"]

        def _load_images(self):
            if self.__icons_loaded:
                return
            color = self.color()
            cls = self.__class__
            cls.EXPANDED_ICON = get_icon_image("chevron_down", 14, 14, color=color)
            cls.COLLAPSED_ICON = get_icon_image("chevron_right", 14, 14, color=color)
            cls.BLANK = get_icon_image("blank", 14, 14)
            cls.__icons_loaded = True

    def __init__(self, node, **kw):
        super(NestedTreeView, self).__init__(node, **kw)
        self.initialize_tree()

    def get_body(self):
        return self

    @property
    def parent_node(self):
        return self._parent_node

    @parent_node.setter
    def parent_node(self, value):
        # allow setting of parent node since this tree is nestable within a node
        self._parent_node = value

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, value):
        self._depth = value - 1
        # Update depth even for child nodes
        for node in self.nodes:
            node.depth = self._depth + 1
