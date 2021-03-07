from formation.handlers import layout, image, misc

_handlers = {
    "attr": misc.AttrHandler,
    "menu": misc.MenuHandler,
    "layout": layout,
    "img": image,
}


def add_handler(handler):
    if not hasattr(handler, "handle"):
        raise ValueError("Missing method handle() in handler {}".format(handler))
    for namespace in getattr(handler, "namespaces", {}):
        _handlers[namespace] = handler


def dispatch_to_handlers(widget, config, **kwargs):
    # collect only handlers that are needed for this particular config
    handlers = [_handlers[n] for n in _handlers if n in config]
    for handler in handlers:
        handler.handle(widget, config, **kwargs)
