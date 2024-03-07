from formation.handlers import layout, image, misc, scroll

_namespace_handlers = {
    "attr": misc.AttrHandler,
    "menu": misc.MenuHandler,
    "layout": layout,
    "img": image,
    "scroll": scroll
}

_handlers = {
    "image": image.parse_image
}


def parse_arg(value, type_=None):
    if type_ is None:
        return value

    if type_ in _handlers:
        return _handlers[type_](value)

    if isinstance(type_, str):
        builtin = getattr(__builtins__, type_, None)
    else:
        builtin = type_

    if builtin:
        return builtin(value)

    return value


def add_namespace_handler(handler):
    if not hasattr(handler, "handle"):
        raise ValueError("Missing method handle() in handler {}".format(handler))
    for namespace in getattr(handler, "namespaces", {}):
        _namespace_handlers[namespace] = handler


def add_handler(typ, handler):
    _handlers[typ] = handler


def dispatch_to_handlers(widget, config, **kwargs):
    # collect only handlers that are needed for this particular config
    handlers = [_namespace_handlers[n] for n in _namespace_handlers if n in config]
    for handler in handlers:
        handler.handle(widget, config, **kwargs)
