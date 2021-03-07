"""
Widget tree for the studio
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

from hoverset.ui.widgets import EventMask, TreeView, Label
from hoverset.ui.windows import DragWindow
from studio.ui.geometry import bounds, upscale_bounds
from studio.ui.highlight import EdgeIndicator


class MalleableTree(TreeView):
    """
    Sub class of TreeView that allows rearrangement of Nodes which useful in repositioning components in the
    various studio features. For any tree view that allows rearrangement, subclass MalleableTree.
    """
    drag_components = []  # All objects that were selected when dragging began
    drag_active = False  # Flag showing whether we are currently dragging stuff
    drag_popup = None  # The almost transparent window that shows what is being dragged
    drag_highlight = None  # The widget that currently contains the rectangular highlight
    drag_select = None  # The node where all events go when button is released ending drag
    drag_display_limit = 3  # The maximum number of items the drag popup can display
    drag_instance = None  # The current tree that is performing a drag

    class Node(TreeView.Node):
        PADDING = 0

        def __init__(self, master=None, **config):
            # Master is always a TreeView object unless you tamper with the add_as_node method
            super().__init__(master, **config)
            # If set tp False the node accepts children and vice versa
            self._is_terminal = config.get("terminal", True)
            self.strip.bind_all("<Motion>", self.drag)
            self.strip.bind_all("<Motion>", self.begin_drag, add='+')
            # use add='+' to avoid overriding the default event which selects nodes
            self.strip.bind_all("<ButtonRelease-1>", self.end_drag, add='+')
            self.strip.config(**self.style.highlight)  # The highlight on a normal day
            self._on_structure_change = None
            self.editable = False
            self.configuration = config

        def on_structure_change(self, callback, *args, **kwargs):
            self._on_structure_change = lambda: callback(*args, **kwargs)

        def _change_structure(self):
            if self._on_structure_change:
                self._on_structure_change()
            self.tree._structure_changed()

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
            widget = self.winfo_containing(event.x_root, event.y_root)
            # The widget can be a child to Node but not necessarily a node but we need a node so
            # Resolve the node that is immediately under the cursor position by iteratively getting widget's parent
            # For the sake of performance not more than 4 iterations
            limit = 4
            while not isinstance(widget, self.__class__):
                if widget is None:
                    # This happens when someone hovers outside the current top level window
                    break
                widget = self.nametowidget(widget.winfo_parent())
                limit -= 1
                if not limit:
                    break
            tree = self.event_first(event, self.tree, MalleableTree)

            if isinstance(widget, MalleableTree.Node):
                # We can only react if we have resolved the widget to a Node object
                widget.react(event)
                # Store the currently reacting widget so we can apply actions to it on ButtonRelease/ drag_end
                MalleableTree.drag_select = widget
            elif isinstance(tree, self.tree.__class__):
                # if the tree found is compatible to the current tree i.e belongs to same class or is subclass of
                # disallow incompatible trees from interacting as this may cause errors
                tree.react(event)
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
                    action = node.react(event)
                    if action == 0:
                        node.insert_before(*MalleableTree.drag_components)
                    elif action == 1:
                        node.insert(None, *MalleableTree.drag_components)
                    elif action == 2:
                        node.insert_after(*MalleableTree.drag_components)
                    # else there is no viable action to take.
                    if action in (0, 1, 2):
                        # These actions means tree structure changed
                        self._change_structure()
                # Reset all drag related attributes
                if MalleableTree.drag_popup is not None:
                    MalleableTree.drag_select.clear_indicators()
                    MalleableTree.drag_popup.destroy()  # remove the drag popup window
                    MalleableTree.drag_popup = None
                    MalleableTree.drag_components = []
                    MalleableTree.drag_instance = None
                    self.clear_indicators()
                    MalleableTree.drag_highlight = None
                MalleableTree.drag_active = False

        def highlight(self):
            MalleableTree.drag_highlight = self
            self.strip.config(**self.style.bright_highlight)

        def react(self, event) -> int:
            # Checks, based on the cursor position whether we can insert before, into or after the node
            # Returns 0, 1 or 2 respectively
            # It is mostly with respect to the nodes head element known as the strip except for --- case * --- below
            self.clear_indicators()
            # The cursor is at the top edge of the node so we can attempt to insert before it
            if event.y_root < self.strip.winfo_rooty() + 5:
                self.tree.edge_indicator.top(upscale_bounds(bounds(self.strip), self))
                return 0
            # The cursor is at the center of the node so we can attempt a direct insert into the node
            elif self.strip.winfo_rooty() + 5 < event.y_root < self.strip.winfo_rooty() + self.strip.height - 5:
                if not self._is_terminal:
                    # If node is terminal then id does not support children and consequently insertion
                    self.highlight()
                    return 1
            # The cursor is at the bottom edge of the node so we attempt to insert immediately after the node
            elif self._expanded:  # --- Case * ---
                # If the node is expanded we would want to edge indicate at the very bottom after its last child
                if event.y_root > self.winfo_rooty() + self.height - 5:
                    self.tree.edge_indicator.bottom(bounds(self))
                    return 2
            else:
                self.tree.edge_indicator.bottom(upscale_bounds(bounds(self.strip), self))
                return 2

        def clear_highlight(self):
            # Remove the rectangular highlight around the node
            self.strip.configure(**self.style.highlight)

        def clear_indicators(self):
            # Remove any remaining node highlights and edge indicators
            if MalleableTree.drag_highlight is not None:
                MalleableTree.drag_highlight.clear_highlight()
            self.tree.edge_indicator.clear()

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

    def __init__(self, master, **config):
        super().__init__(master, **config)
        self._on_structure_change = None
        self.is_terminal = False
        self.edge_indicator = EdgeIndicator(self)  # A line that shows where an insertion can occur

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
            self.edge_indicator.clear()
        super().insert(index, *nodes)
        # Return the nodes just in case they have been cloned and new references are required
        return nodes

    def react(self, *_):
        self.clear_indicators()
        self.highlight()
        # always perform a direct insert hence return 1
        return 1

    def highlight(self):
        MalleableTree.drag_highlight = self
        self.config(**self.style.bright_highlight)

    def clear_highlight(self):
        # Remove the rectangular highlight around the node
        self.configure(**self.style.highlight)

    def clear_indicators(self):
        # Remove any remaining node highlights and edge indicators
        if MalleableTree.drag_highlight is not None:
            MalleableTree.drag_highlight.clear_highlight()
            self.edge_indicator.clear()
