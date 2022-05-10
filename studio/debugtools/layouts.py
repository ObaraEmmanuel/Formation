import tkinter
from tkinter import ttk

from studio.lib import layouts


def _filtered_def(defs):
    # remove common width and height params included in studio layout defs
    return dict(filter(lambda x: x[0] not in ('width', 'height'), defs.items()))


class BaseLayout:
    defs = {}
    name = ''

    @classmethod
    def get_def(cls, widget):
        info = cls.configure(widget)
        # Ensure we use the dynamic definitions
        definition = dict(cls.defs)
        for key in definition:
            # will throw a key error if a definition value is not found in info
            definition[key]["value"] = info[key]
        return definition

    @classmethod
    def configure(cls, widget, **kw):
        if not kw:
            return {}

    @classmethod
    def verify(cls, widget):
        return True


class PackLayout(BaseLayout):
    defs = _filtered_def(layouts.PackLayoutStrategy.DEFINITION)
    name = 'Pack'

    @classmethod
    def configure(cls, widget, **kw):
        if not kw:
            return widget.pack_info() or {}
        widget.pack_configure(**kw)


class PlaceLayout(BaseLayout):
    defs = layouts.PlaceLayoutStrategy.DEFINITION
    name = 'Place'

    @classmethod
    def configure(cls, widget, **kw):
        if not kw:
            return widget.place_info() or {}
        widget.place_configure(**kw)


class GridLayout(BaseLayout):
    defs = _filtered_def(layouts.GridLayoutStrategy.DEFINITION)
    name = 'Grid'

    @classmethod
    def configure(cls, widget, **kw):
        if not kw:
            return widget.grid_info() or {}
        widget.grid_configure(**kw)


class TabLayout(BaseLayout):
    defs = _filtered_def(layouts.TabLayoutStrategy.DEFINITION)
    name = 'Notebook'

    @classmethod
    def configure(cls, widget, **kw):
        parent = widget.master
        if isinstance(parent, ttk.Notebook):
            if not kw:
                return parent.tab(widget) or {}
            parent.tab(widget, **kw)

    @classmethod
    def verify(cls, widget):
        parent = widget.master
        return isinstance(parent, ttk.Notebook)


class PanedLayout(BaseLayout):
    defs = _filtered_def(layouts.PanedLayoutStrategy.DEFINITION)
    name = 'Pane'

    @classmethod
    def configure(cls, widget, **kw):
        parent = widget.master
        if cls.verify(widget):
            if not kw:
                info = parent.paneconfig(widget) or {}
                return {k: info[k][-1] for k in info}
            parent.paneconfig(widget, **kw)

    @classmethod
    def verify(cls, widget):
        parent = widget.master
        return isinstance(parent, tkinter.PanedWindow) and not isinstance(parent, ttk.PanedWindow)


class NPanedLayout(BaseLayout):
    defs = _filtered_def(layouts.NPanedLayoutStrategy.DEFINITION)
    name = 'Pane'

    @classmethod
    def configure(cls, widget, **kw):
        parent = widget.master
        if cls.verify(widget):
            if not kw:
                return parent.pane(widget) or {}
            parent.pane(widget, **kw)

    @classmethod
    def verify(cls, widget):
        parent = widget.master
        return isinstance(parent, ttk.PanedWindow)


_layout_map = {
    'pack': PackLayout,
    'grid': GridLayout,
    'place': PlaceLayout,
    'notebook': TabLayout,
    'panedwindow': None,
    'wm': None,
    'canvas': None,
    'text': None,
}


def get_layout(widget) -> BaseLayout:
    if not widget or not widget.winfo_ismapped():
        return None
    manager = widget.winfo_manager()
    if manager == 'panedwindow':
        if isinstance(widget.master, ttk.PanedWindow):
            return NPanedLayout
        elif isinstance(widget.master, tkinter.PanedWindow):
            return PanedLayout
        else:
            return None
    else:
        layout = _layout_map.get(manager, None)

    if layout and layout.verify(widget):
        return layout
