import tkinter as tk
import tkinter.ttk as ttk

from formation.handlers import image

namespaces = {
    "layout": "http://www.hoversetformationstudio.com/layouts/",
}

_redirect = {
    "image": image
}


def set_grid(widget, _=None, **options):
    for opt in list(options):
        if opt in ("width", "height"):
            widget[opt] = options.pop(opt)
    widget.grid(**options)


def set_pack(widget, _=None, **options):
    for opt in list(options):
        if opt in ("width", "height"):
            widget[opt] = options.pop(opt)
    widget.pack(**options)


def set_place(widget, _=None, **options):
    widget.place(**options)


def set_tab(widget, parent, **options):
    if widget not in parent.tabs():
        parent.add(widget)
    parent.tab(widget, **options)


def set_pane(widget, parent, **options):
    parent.add(widget, **options)


_layout_handlers = {
    "place": set_place,
    "pack": set_pack,
    "grid": set_grid,
    "TabLayout": set_tab,
    "PanedLayout": set_pane,
    "NativePanedLayout": set_pane,

    # backward compatibility for old layout names

    "FrameLayout": set_place,
    "LinearLayout": set_pack,
    "GridLayout": set_grid,
}


def get_layout_handler(parent_node, parent):
    layout = None if parent_node is None else parent_node["attr"].get("layout")
    if layout is not None:
        return _layout_handlers.get(layout)
    if parent.__class__ == ttk.Notebook:
        return set_tab
    if parent.__class__ == tk.PanedWindow:
        return set_pane
    if parent.__class__ == ttk.PanedWindow:
        return set_pane


def handle(widget, config, **kwargs):
    parent = kwargs.get("parent")
    if parent is None:
        return
    parent_node = kwargs.get("parent_node")
    layout = get_layout_handler(parent_node, parent)
    if layout is None:
        return

    def handle_method(**kw):
        layout(widget, parent, **kw)

    cnf = kwargs.get("extra_config", config.get("layout", {}))
    direct_config = {}
    for prop in cnf:
        if prop in _redirect:
            _redirect[prop].handle(widget, config, **kwargs, extra_config={prop: cnf[prop]},
                                   handle_method=handle_method)
            continue
        # accumulate config that can be handled directly
        direct_config[prop] = cnf[prop]
    handle_method(**direct_config)
