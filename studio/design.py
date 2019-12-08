"""
Drag drop designer for the studio
"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

from hoverset.ui.widgets import Frame, EventWrap
from studio.highlight import HighLight
from studio.layouts import BaseLayout
from studio.lib.layouts import FrameLayout

import studio.geometry as geometry
from studio.lib.pseudo import PseudoWidget


class Designer(Frame):

    def __init__(self, master, studio):
        super().__init__(master)
        self.studio = studio
        self.config(**self.style.bright)
        self.objects = []
        self.highlight = HighLight(self)
        self.highlight.on_resize(self._on_size_changed)
        self.highlight.on_move(self._on_move)
        self.highlight.on_release(self._on_release)
        self.current_obj = None
        self.current_layout = None
        self.bind("<Button-1>", lambda *_: self.select(None))
        self._padding = 30
        # Initialize the first layout some time after the designer has been initialized
        self.after(300, self._set_layout)

    def _set_layout(self):
        self.add(FrameLayout, self._padding, self._padding, width=self.width - self._padding * 2,
                 height=self.height - self._padding * 2)

    @property
    def _ids(self):
        return [i.id for i in self.objects]

    def add(self, obj_class: PseudoWidget.__class__, x, y, **kwargs):
        width = kwargs.get("width", 55)
        height = kwargs.get("height", 30)
        count = 1
        name = f"{obj_class.display_name}_{count}"
        while name in self._ids:
            name = f"{obj_class.display_name}_{count}"
            count += 1
        obj = obj_class(self, name)
        setattr(obj, "level", 0)
        setattr(obj, "layout", self)
        self.objects.append(obj)
        obj.bind("<Button-1>", lambda _: self.select(obj))

        layout = kwargs.get("layout")
        if isinstance(layout, BaseLayout):
            bounds = (x, y, x+width, y+height)
            bounds = geometry.resolve_bounds(bounds, self)
            layout.add_widget(obj, bounds)
            self.studio.add(obj, layout)
        else:
            obj.place(in_=self, x=x, y=y, width=width, height=height, bordermode="outside")
            self.studio.add(obj, None)

    def select_layout(self, layout: BaseLayout):
        pass

    def react(self, event):
        layout = self.event_first(event, self, BaseLayout)
        if self.current_layout is not None:
            self.current_layout.clear_highlight()
            self.current_layout = None
        if isinstance(layout, BaseLayout):
            self.current_layout = layout
            layout.highlight()

    def compute_overlap(self, bound1, bound2):
        return geometry.compute_overlap(bound1, bound2)

    def layout_at(self, bounds):
        for layout in sorted(filter(lambda x: isinstance(x, BaseLayout) and x != self.current_obj, self.objects),
                             key=lambda x: len(self.objects) - x.level):
            if isinstance(self.current_obj, BaseLayout) and self.current_obj.level < layout.level:
                continue
            if self.compute_overlap(layout.bounds(), bounds):
                return layout
        return None

    def parse_bounds(self, bounds):
        return {
            "x": bounds[0],
            "y": bounds[1],
            "width": bounds[2] - bounds[0],
            "height": bounds[3] - bounds[1]
        }

    def select(self, obj):
        if obj is None:
            self.clear_highlight()
            self.studio.select(None)
            return
        if self.current_obj == obj:
            return
        self.clear_highlight()
        self.current_obj = obj
        self.draw_highlight(obj)
        self.studio.select(obj)

    def draw_highlight(self, obj):
        self.highlight.surround(obj)

    def clear_highlight(self):
        if self.highlight is not None:
            self.highlight.clear()
            self.current_obj = None
            if self.current_layout is not None:
                self.current_layout.clear_highlight()
                self.current_layout = None

    def _on_release(self, bound):
        if self.current_layout is not None and self.current_obj is not None and self.current_layout != self.current_obj:
            print("Releasing to layout")
            self.current_layout.clear_highlight()
            self.current_layout.add_widget(self.current_obj, bound)
            self.adjust_highlight(self.current_obj)

    def adjust_highlight(self, widget):
        self.highlight.adjust_to(self.highlight.bounds_from_object(widget))

    def _on_move(self, new_bound):
        if self.current_obj is not None:
            layout: BaseLayout = self.layout_at(new_bound)
            if layout is not None and self.current_obj != layout:
                if layout != self.current_layout:
                    if self.current_layout is not None:
                        self.current_layout.clear_highlight()
                    layout.highlight()
                    self.current_layout = layout
                layout.move_widget(self.current_obj, new_bound)
            else:
                if self.current_layout is not None:
                    self.current_layout.clear_highlight()
                    self.current_layout = None
                self.current_obj.level = 0
                self.current_obj.layout = self
                self.current_obj.place(in_=self, **self.parse_bounds(new_bound), bordermode="outside")
            self.current_obj.update_idletasks()
            self.update_idletasks()

    def _on_size_changed(self, new_bound):
        if self.current_obj is None:
            return
        if isinstance(self.current_obj.layout, BaseLayout):
            self.current_obj.layout.resize_widget(self.current_obj, new_bound)
        else:
            self.current_obj.level = 0
            self.current_obj.place(in_=self, **self.parse_bounds(new_bound), bordermode="outside")
        self.current_obj.update_idletasks()
        self.update_idletasks()
