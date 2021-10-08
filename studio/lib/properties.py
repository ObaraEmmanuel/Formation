"""
Contains all the widget properties used in the designer and specifies all the styles that can be applied to a widget
"""
# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #

from hoverset.platform import platform_is, MAC, WINDOWS

BUILTIN_CURSORS = (
    'arrow', 'based_arrow_down', 'based_arrow_up', 'boat',
    'bogosity', 'bottom_left_corner', 'bottom_right_corner',
    'bottom_side', 'bottom_tee', 'box_spiral', 'center_ptr',
    'circle', 'clock', 'coffee_mug', 'cross', 'cross_reverse',
    'crosshair', 'diamond_cross', 'dot', 'dotbox', 'double_arrow',
    'draft_large', 'draft_small', 'draped_box', 'exchange', 'fleur',
    'gobbler', 'gumby', 'hand1', 'hand2', 'heart', 'icon',
    'iron_cross', 'left_ptr', 'left_side', 'left_tee', 'leftbutton',
    'll_angle', 'lr_angle', 'man', 'middlebutton', 'mouse', 'none',
    'pencil', 'pirate', 'plus', 'question_arrow', 'right_ptr',
    'right_side', 'right_tee', 'rightbutton', 'rtl_logo',
    'sailboat', 'sb_down_arrow', 'sb_h_double_arrow',
    'sb_left_arrow', 'sb_right_arrow', 'sb_up_arrow',
    'sb_v_double_arrow', 'shuttle', 'sizing', 'spider', 'spraycan',
    'star', 'target', 'tcross', 'top_left_arrow', 'top_left_corner',
    'top_right_corner', 'top_side', 'top_tee', 'trek', 'ul_angle',
    'umbrella', 'ur_angle', 'watch', 'xterm', 'X_cursor')

BUILTIN_CURSORS_WINDOWS = (
    'no', 'starting', 'size', 'size_ne_sw', 'size_ns', 'size_nw_se', 'size_we', 'uparrow', 'wait'
)

BUILTIN_CURSORS_MAC = (
    'copyarrow', 'aliasarrow', 'contextualmenuarrow', 'text',
    'cross-hair', 'closedhand', 'openhand', 'pointinghand',
    'resizeleft', 'resizeright', 'resizeleftright', 'resizeup',
    'resizedown', 'resizeupdown', 'notallowed', 'poof',
    'countinguphand', 'countingdownhand', 'countingupanddownhand', 'spinning'
)

BUILTIN_BITMAPS = (
    'error', 'gray75', 'gray50', 'gray25', 'gray12',
    'hourglass', 'info', 'questhead', 'question', 'warning',
)

BUILTIN_BITMAPS_MAC = (
    'document', 'stationery', 'edition', 'application', 'accessory',
    'forder', 'pfolder', 'trash', 'floppy', 'ramdisk', 'cdrom',
    'preferences', 'querydoc', 'stop', 'note', 'caution'
)

if platform_is(MAC):
    BUILTIN_BITMAPS = BUILTIN_BITMAPS + BUILTIN_BITMAPS_MAC


def all_cursors() -> tuple:
    """
    Get all cursors in the cursor database regardless of the platform they belong to
    :return: Tuple of strings
    """
    return BUILTIN_CURSORS + BUILTIN_CURSORS_WINDOWS + BUILTIN_CURSORS_MAC


def all_supported_cursors() -> tuple:
    """
    Get all cursors from the database that are supported in the current operating system
    :return: Tuple of strings
    """
    if platform_is(MAC):
        return BUILTIN_CURSORS + BUILTIN_CURSORS_MAC
    if platform_is(WINDOWS):
        return BUILTIN_CURSORS + BUILTIN_CURSORS_WINDOWS
    return BUILTIN_CURSORS


PROPERTY_TABLE = {
    "activebackground": {
        "display_name": "active background",
        "type": "color",
    },
    "activeborderwidth": {
        "display_name": "active border width",
        "type": "dimension",
        "units": "pixels"
    },
    "activeforeground": {
        "display_name": "active foreground",
        "type": "color",
    },
    "activerelief": {
        "display_name": "active relief",
        "type": "relief",
    },
    "activestyle": {
        "display_name": "active style",
        "type": "choice",
        "options": ("none", "dotbox", "underline")
    },
    "anchor": {
        "display_name": "anchor",
        "type": "anchor",
        "multiple": False
    },
    "aspect": {
        "display_name": "aspect",
        "type": "dimension",
        "units": "percentage"
    },
    "autoseparators": {
        "display_name": "autoseparators",
        "type": "boolean",
    },
    "background": {
        "display_name": "background",
        "type": "color",
    },
    "bitmap": {
        "display_name": "bitmap",
        "type": "bitmap",
    },
    "blockcursor": {
        "display_name": "blockcursor",
        "type": "boolean",
    },
    "borderwidth": {
        "display_name": "relief width",
        "type": "dimension",
        "units": "pixels"
    },
    "buttoncursor": {
        "display_name": "button cursor",
        "type": "cursor",
    },
    "buttondownrelief": {
        "display_name": "down button relief",
        "type": "relief",
    },
    "buttonuprelief": {
        "display_name": "up button relief",
        "type": "relief",
    },
    "command": {
        "display_name": "command",
        "type": "callback",
    },
    "compound": {
        "display_name": "compound",
        "type": "choice",
        "options": ("center", "none", "top", "bottom", "left", "right")
    },
    "confine": {
        "display_name": "confine",
        "type": "boolean",
    },
    "cursor": {
        "display_name": "cursor",
        "type": "cursor",
    },
    "direction": {
        "display_name": "direction",
        "type": "choice",
        "options": ("above", "below", "flush", "left", "right")
    },
    "disabledbackground": {
        "display_name": "disabled background",
        "type": "color",
    },
    "disabledforeground": {
        "display_name": "disabled foreground",
        "type": "color",
    },
    "exportselection": {
        "display_name": "export selection",
        "type": "boolean",
    },
    "font": {
        "display_name": "font",
        "type": "font",
    },
    "foreground": {
        "display_name": "foreground",
        "type": "color",
    },
    "format": {
        "display_name": "format",
        "type": "text",
    },
    "from": {
        "display_name": "from",
        "type": "float",
    },
    "handlepad": {
        "display_name": "handle pad",
        "type": "dimension",
        "units": "pixels",
        "default": 8
    },
    "handlesize": {
        "display_name": "handle size",
        "type": "dimension",
        "units": "pixels",
        "default": 8
    },
    "highlightbackground": {
        "display_name": "border color",
        "type": "color",
    },
    "highlightcolor": {
        "display_name": "active border color",
        "type": "color",
    },
    "highlightthickness": {
        "display_name": "border width",
        "type": "dimension",
        "units": "pixels",
    },
    "image": {
        "display_name": "image",
        "type": "image",
    },
    "inactiveselectbackground": {
        "display_name": "inactive select background",
        "type": "color",
    },
    "increment": {
        "display_name": "increment",
        "type": "float",
    },
    "indicatoron": {
        "display_name": "indicator on",
        "type": "boolean",
    },
    "insertbackground": {
        "display_name": "insert background",
        "type": "color",
    },
    "insertborderwidth": {
        "display_name": "insert border width",
        "type": "dimension",
        "units": "pixels",
    },
    "insertofftime": {
        "display_name": "insertofftime",
        "type": "duration",
        "units": "ms",
    },
    "insertontime": {
        "display_name": "insertontime",
        "type": "duration",
        "units": "ms",
    },
    "insertunfocussed": {
        "display_name": "insert unfocused",
        "type": "choice",
        "options": ("none", "hollow", "solid")
    },
    "insertwidth": {
        "display_name": "insert width",
        "type": "dimension",
        "units": "pixels",
    },
    "invalidcommand": {
        "display_name": "invalid command",
        "type": "callback",
    },
    "jump": {
        "display_name": "jump",
        "type": "boolean",
    },
    "justify": {
        "display_name": "justify",
        "type": "choice",
        "options": ("left", "center", "right")
    },
    "label": {
        "display_name": "label",
        "type": "text",
    },
    "labelanchor": {
        "display_name": "label anchor",
        "type": "anchor",
        "multiple": False,
    },
    "length": {
        "display_name": "length",
        "type": "dimension",
        "units": "pixels",
    },
    "listvariable": {
        "display_name": "listvariable",
        "type": "stringvariable",
    },
    "maxundo": {
        "display_name": "maxundo",
        "type": "number",
    },
    "offrelief": {
        "display_name": "off relief",
        "type": "relief",
    },
    "offvalue": {
        "display_name": "off value",
        "type": "text",
    },
    "onvalue": {
        "display_name": "on value",
        "type": "text",
    },
    "opaqueresize": {
        "display_name": "opaqueresize",
        "type": "boolean",
    },
    "orient": {
        "display_name": "orient",
        "type": "choice",
        "options": ("vertical", "horizontal")
    },
    "overrelief": {
        "display_name": "over relief",
        "type": "relief",
    },
    "padx": {
        "display_name": "horizontal padding",
        "type": "dimension",
        "units": "pixels",
    },
    "pady": {
        "display_name": "vertical padding",
        "type": "dimension",
        "units": "pixels",
    },
    "postcommand": {
        "display_name": "postcommand",
        "type": "callback",
    },
    "proxybackground": {
        "display_name": "proxy background",
        "type": "color",
    },
    "proxyborderwidth": {
        "display_name": "proxy border width",
        "type": "dimension",
        "units": "pixels",
    },
    "proxyrelief": {
        "display_name": "proxy relief",
        "type": "relief",
    },
    "readonlybackground": {
        "display_name": "readonly background",
        "type": "color",
    },
    "relief": {
        "display_name": "relief",
        "type": "relief",
    },
    "repeatdelay": {
        "display_name": "repeat delay",
        "type": "duration",
        "units": "ms",
    },
    "repeatinterval": {
        "display_name": "repeat interval",
        "type": "duration",
        "units": "ms",
    },
    "resolution": {
        "display_name": "resolution",
        "type": "number",
    },
    "sashpad": {
        "display_name": "sash padding",
        "type": "dimension",
        "units": "pixels",
    },
    "sashrelief": {
        "display_name": "sash relief",
        "type": "relief",
    },
    "sashwidth": {
        "display_name": "sash width",
        "type": "dimension",
        "units": "pixels",
    },
    "selectbackground": {
        "display_name": "select background",
        "type": "color",
    },
    "selectborderwidth": {
        "display_name": "select border width",
        "type": "dimension",
        "units": "pixels",
    },
    "selectforeground": {
        "display_name": "select foreground",
        "type": "color",
    },
    "selectimage": {
        "display_name": "select image",
        "type": "image",
    },
    "selectmode": {
        "display_name": "select mode",
        "type": "choice",
        "options": ("browse", "single", "multiple", "extended")
    },
    "setgrid": {
        "display_name": "setgrid",
        "type": "boolean",
    },
    "show": {
        "display_name": "show",
        "type": "text",
    },
    "showhandle": {
        "display_name": "show handle",
        "type": "boolean",
    },
    "showvalue": {
        "display_name": "show value",
        "type": "boolean",
    },
    "sliderlength": {
        "display_name": "slider length",
        "type": "dimension",
        "units": "pixels",
    },
    "sliderrelief": {
        "display_name": "slider relief",
        "type": "relief",
    },
    "spacing1": {
        "display_name": "top spacing",
        "type": "dimension",
        "units": "pixels",
    },
    "spacing2": {
        "display_name": "line spacing",
        "type": "dimension",
        "units": "pixels",
    },
    "spacing3": {
        "display_name": "bottom spacing",
        "type": "dimension",
        "units": "pixels",
    },
    "state": {
        "display_name": "state",
        "type": "choice",
        "options": ("normal", "disabled")
    },
    "tabstyle": {
        "display_name": "tab style",
        "type": "choice",
        "options": ("tabular", "wordprocessor")
    },
    "takefocus": {
        "display_name": "focusable",
        "type": "boolean",
    },
    "tearoff": {
        "display_name": "tearoff",
        "type": "boolean",
    },
    "tearoffcommand": {
        "display_name": "tear-off command",
        "type": "callback",
    },
    "text": {
        "display_name": "text",
        "type": "textarea",
    },
    "textvariable": {
        "display_name": "textvariable",
        "type": "variable",
    },
    "tickinterval": {
        "display_name": "tick interval",
        "type": "duration",
        "units": "ms"
    },
    "title": {
        "display_name": "title",
        "type": "text",
    },
    "to": {
        "display_name": "to",
        "type": "float",
    },
    "tristateimage": {
        "display_name": "tri-state image",
        "type": "image",
    },
    "tristatevalue": {
        "display_name": "tri-state value",
        "type": "color",
    },
    "troughcolor": {
        "display_name": "trough color",
        "type": "color",
    },
    "underline": {
        "display_name": "underline",
        "type": "number",
    },
    "undo": {
        "display_name": "undo",
        "type": "boolean",
    },
    "validate": {
        "display_name": "validate",
        "type": "choice",
        "options": ("none", "focus", "focusin", "focusout", "key", "all")
    },
    "validatecommand": {
        "display_name": "validate command",
        "type": "callback",
    },
    "value": {
        "display_name": "value",
        "type": "text",
    },
    "variable": {
        "display_name": "variable",
        "type": "variable",
    },
    "wrap": {
        "display_name": "wrap",
        "type": "boolean",
    },
    "wraplength": {
        "display_name": "wraplength",
        "type": "dimension",
        "units": "pixels"
    },
    "mode": {
        "display_name": "mode",
        "type": "choice",
        "options": ("determinate", "indeterminate")
    },
    "xscrollcommand": {
        "display_name": "xscrollcommand",
        "type": "command",
    },
    "xscrollincrement": {
        "display_name": "xscrollincrement",
        "type": "dimension",
        "units": "pixels"
    },
    "yscrollcommand": {
        "display_name": "yscrollcommand",
        "type": "command",
    },
    "yscrollincrement": {
        "display_name": "yscrollincrement",
        "type": "dimension",
        "units": "pixels"
    },
}

_unimplemented = {
    "_colormap": {
        "display_name": "colormap",
        "type": "color",
    },
    "_container": {
        "display_name": "container",
        "type": "boolean",
    },
    "_endline": {
        "display_name": "endline",
        "type": "color",
    },
    "_labelwidget": {
        "display_name": "label widget",
        "type": "color",
    },
    "_menu": {
        "display_name": "menu",
        "type": "color",
    },
    "_offset": {
        "display_name": "offset",
        "type": "color",
    },
    "_startline": {
        "display_name": "startline",
        "type": "color",
    },
    "_tabs": {
        "display_name": "tabs",
        "type": "color",
    },
    "_use": {
        "display_name": "use",
        "type": "color",
    },
    "_type": {
        "display_name": "type",
        "type": "color",
    },
    "_values": {
        "display_name": "values",
        "type": "color",
    },
    "_visual": {
        "display_name": "visual",
        "type": "color",
    },
}

WIDGET_IDENTITY = {
    "class": {
        "display_name": "class",
        "type": "text",
        "readonly": True,
        "name": "class"
    },
    "id": {
        "display_name": "widget id",
        "type": "text",
        "readonly": False,
        "name": "id"
    },
}


def get_resolved(prop, overrides, *property_tables):
    """
    Return copy of the first definition found in a set of property tables.
    The table with the highest priority is passed in first in the
    arguments. Returns empty dict if property cannot be found.
    It also sets the name property and applies overrides
    """
    for table in property_tables:
        if prop in table:
            # use a copy to avoid messing up the general definition
            definition = dict(table[prop], name=prop)
            definition.update(overrides.get(prop, {}))
            return definition
    return {}


def get_properties(widget):
    properties = widget.config()
    resolved_properties = {}
    overrides = getattr(widget, "DEF_OVERRIDES", {})
    for prop in properties:
        definition = get_resolved(prop, overrides, PROPERTY_TABLE)
        if definition:
            definition.update(value=widget[prop])
            resolved_properties[prop] = definition

    return resolved_properties
