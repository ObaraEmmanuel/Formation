"""
Layout classes uses in the studio
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #
from hoverset.ui.icons import get_icon
from hoverset.ui.widgets import Frame
import studio.geometry as geometry
from studio.lib.pseudo import PseudoWidget, Groups


class BaseLayout(Frame):
    VERTICAL = 0x45
    HORIZONTAL = 0x46

    def __init__(self, master):
        super().__init__(master)
        self.parent = master
        self._children = []
        self._temporal_children = []
        self.level = 0

    def highlight(self, *_):
        self.config(**self.style.dark_highlight_active_heavy)

    def clear_highlight(self):
        self.config(highlightthickness=0)
        self._temporal_children = []

    def bounds(self):
        return geometry.bounds(self)

    def add_widget(self, widget, bounds):
        widget.level = self.level + 1
        widget.layout = self
        raise NotImplementedError()

    def lift(self, *_):
        super().lift(*_)
        for child in self._children:
            child.lift(self)

    def move_widget(self, widget, bounds):
        if widget in self._children:
            self.remove_widget(widget)
        if widget not in self._temporal_children:
            self._temporal_children.append(widget)
            widget.level = self.level + 1
            widget.layout = self
            print("lifting")
            widget.lift(self)
        self.resize_widget(widget, bounds)

    def resize_widget(self, widget, bounds):
        bounds = geometry.relative_bounds(bounds, self)  # Make the bounds relative to the layout for proper positioning
        place_bounds = self.parse_bounds(bounds)
        widget.place(in_=self, **place_bounds, bordermode="outside")

    def remove_widget(self, widget):
        if widget in self._temporal_children:
            self._children.remove(widget)
        if widget in self._temporal_children:
            self._temporal_children.remove(widget)

    def parse_bounds(self, bounds):
        return {
            "x": bounds[0],
            "y": bounds[1],
            "width": bounds[2] - bounds[0],
            "height": bounds[3] - bounds[1]
        }

    def add_new(self, widget, x, y):
        self.parent.add(widget, x, y, layout=self)


class FrameLayout(BaseLayout):

    def add_widget(self, widget, bounds):
        super().remove_widget(widget)
        self.move_widget(widget, bounds)
        self._children.append(widget)

    def remove_widget(self, widget):
        super().remove_widget(widget)
        widget.place_forget()


class LinearLayout(BaseLayout):

    def __init__(self, master=None):
        super().__init__(master)
        self._orientation = self.HORIZONTAL

    def add_widget(self, widget, bounds):
        super().remove_widget(widget)
        if self._orientation == self.HORIZONTAL:
            widget.pack(in_=self, fill="x")
        elif self._orientation == self.VERTICAL:
            widget.pack(in_=self, side="left", fill="y")
        self._children.append(widget)

    def remove_widget(self, widget):
        super().remove_widget(widget)
        widget.pack_forget()

    def set_orientation(self, orient):
        if orient == self.VERTICAL:
            self.clear_children()
            for child in self._children:
                child.pack(in_=self, side="left", fill="y")
        elif orient == self.HORIZONTAL:
            self.clear_children()
            for child in self._children:
                child.pack(in_=self, side="top", fill="x")
        else:
            raise ValueError("Value must be BaseLayout.HORIZONTAL or BaseLayout.VERTICAL")


class GenericLinearLayout(BaseLayout):

    def __init__(self, master=None):
        super().__init__(master)
        self._orientation = self.HORIZONTAL
        self._children = []

    def get_last(self):
        if len(self._children):
            last = self._children[-1]
            last.update_idletasks()
            return last.winfo_y() - self.winfo_y() + last.winfo_height()
        else:
            return 0

    def get_offset(self, index):
        if index >= 0:
            last = self._children[index]
            last.update_idletasks()
            return last.winfo_y() - self.winfo_y() + last.winfo_height()
        else:
            return 0

    def add_widget(self, widget, bounds):
        self.attach(widget, widget.winfo_width(), widget.winfo_height())
        self._children.append(widget)

    def attach(self, widget, width, height):
        y = self.get_last()
        widget.place(in_=self, x=0, y=y, width=width, height=height, bordermode="outside")

    def redraw(self, widget):
        from_ = self._children.index(widget)
        temp = self._children[from_:]
        self._children = self._children[:from_]
        dimensions = {}
        for child in temp:
            dimensions[child] = [child.winfo_width(), child.winfo_height()]
            child.place_forget()
        for child in temp:
            self.attach(child, *dimensions[child])
            self._children.append(child)

    def resize_widget(self, widget, bounds):
        super().resize_widget(widget, bounds)
        self.redraw(widget)

    def remove_widget(self, widget):
        from_ = self._children.index(widget)
        dimensions = {}
        for child in self._children[from_:]:
            dimensions[child] = [child.winfo_width(), child.winfo_height()]
            child.place_forget()
        temp = self._children[from_ + 1:]
        self._children = self._children[:from_]
        for child in temp:
            self.attach(child, *dimensions[child])
            self._children.append(child)


class VerticalLinearLayout(LinearLayout):

    def __init__(self, master=None):
        super().__init__(master)
        self._orientation = self.VERTICAL
