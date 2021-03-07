command_props = (
    "command",
    "invalidcommand",
    "postcommand",
    "tearoffcommand",
    "validatecommand",
    "xscrollcommand",
    "yscrollcommand"
)


def handle(widget, config, **kwargs):
    props = dict(kwargs.get("extra_config", {}))
    builder = kwargs.get("builder")
    # add the command name and value to command map for deferred
    # connection to the actual methods
    for prop in props:
        builder._command_map.append((
            prop,
            props[prop],
            kwargs.get("handle_method")
        ))
