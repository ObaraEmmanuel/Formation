from formation.handlers import image, command


class VariableHandler:

    @classmethod
    def handle(cls, widget, config, **kwargs):
        builder = kwargs.get("builder")
        properties = kwargs.get("extra_config", {})
        handle_method = kwargs.get("handle_method", getattr(widget, "config", None))
        if handle_method is None:
            # no way to assign the variable so just stop here
            return
        for prop in properties:
            # find the variable which will be preloaded on the builder
            handle_method(**{prop: getattr(builder, properties[prop], '')})


_common_redirect = {
    "image": image,
    "selectimage": image,
    "tristateimage": image,
    "textvariable": VariableHandler,
    "variable": VariableHandler,
    "listvariable": VariableHandler,
    # extend with command types
    **{prop: command for prop in command.command_props},
}


class MenuHandler:
    _redirect = _common_redirect

    namespaces = {
        "menu": "http://www.hoversetformationstudio.com/menu",
    }

    @classmethod
    def handle(cls, _, config, **kwargs):
        menu = kwargs.get("menu")
        index = kwargs.get("index")
        if menu is None or index is None:
            # without menu and index we cant really do much
            return
        attributes = config.get("menu", {})

        def handle_method(**conf):
            menu.entryconfigure(index, **conf)

        for attr in attributes:
            if attr in cls._redirect:
                extra = {
                    "extra_config": {attr: attributes[attr]},
                    "handle_method": handle_method
                }
                cls._redirect[attr].handle(None, config, **kwargs, **extra)
                continue
            handle_method(**{attr: attributes[attr]})


class AttrHandler:
    _ignore = (
        "layout", "menu"
    )

    _redirect = _common_redirect

    namespaces = {
        "attr": "http://www.hoversetformationstudio.com/styles/",
    }

    @classmethod
    def handle(cls, widget, config, **kwargs):
        attributes = config.get("attr", {})
        handle_method = kwargs.get("handle_method", widget.config)
        # update handle method just in case it was missing
        kwargs.update(handle_method=handle_method)
        direct_config = {}
        for attr in attributes:
            if attr in cls._ignore:
                continue
            if attr in cls._redirect:
                cls._redirect[attr].handle(widget, config, **kwargs, extra_config={attr: attributes[attr]})
                continue
            direct_config[attr] = attributes[attr]
        handle_method(**direct_config)
