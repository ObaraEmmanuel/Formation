from collections import defaultdict

namespaces = {
    "layout": "http://www.hoversetformationstudio.com/scroll/",
}

_redirect = {}


def handle(widget, config, **kwargs):
    builder = kwargs.get("builder")
    if not hasattr(builder, "_scroll_map"):
        builder._scroll_map = defaultdict(lambda: defaultdict(list))
    props = config.get("scroll", {})

    if "x" in props:
        builder._scroll_map[props["x"]]["x"].append(widget)

    if "y" in props:
        builder._scroll_map[props["y"]]["y"].append(widget)


def build_scroll_command(widgets):
    def scroll_command(*args):
        for widget in widgets["y"]:
            widget.yview(*args)
        for widget in widgets["x"]:
            widget.xview(*args)

    return scroll_command


def build_widget_scroll_command(scrollbar, widget, widgets):
    def scroll_command(*args):
        scrollbar.set(*args)
        for w in widgets["y"]:
            if w != widget:
                w.yview("moveto", args[0])
        for w in widgets["x"]:
            if w != widget:
                w.xview("moveto", args[0])

    return scroll_command


def apply_scroll_config(builder, scroll_map):
    for scroll, widgets_xy in scroll_map.items():
        scroll = getattr(builder, scroll, None)
        if not scroll:
            continue
        scroll.config(command=build_scroll_command(widgets_xy))

        for widget in widgets_xy["x"]:
            widget.config(xscrollcommand=build_widget_scroll_command(scroll, widget, widgets_xy))

        for widget in widgets_xy["y"]:
            widget.config(yscrollcommand=build_widget_scroll_command(scroll, widget, widgets_xy))





