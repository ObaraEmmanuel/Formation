import os
import logging

from hoverset.data.preferences import *
from hoverset.data.keymap import ShortcutPane

logger = logging.getLogger("Pref")

defaults = {
    "studio": {
        "recent": [],
        "recent_max": 20,
        "recent_max_length": 70,
        "recent_show": "name",
        "panes": {
            "right": {
                "width": 320,
            },
            "center": {
                "width": 400
            },
            "left": {
                "width": 320
            }
        },
        "pos": {
            "geometry": '',
            "state": 'zoomed'
        },
        "on_startup": "new",
        "prev_contexts": [],
        "smoothness": 3,
        "use_undo_depth": True,
        "undo_depth": 30,
        "custom_widget_paths": []
    },
    "features": {},
    "hotkeys": {},
    "designer": {
        "frame_skip": 4,
        "xml": {
            "pretty_print": True,
        },
        "json": {
            "compact": False,
            "pretty_print": True,
            "indent": "",
            "indent_count": 4,
            "sort_keys": True,
            "stringify_values": True
        },
        "image_path": 'mixed',
        "descriptive_names": False,
        "label": {
            "start": 1,
            "underscore": True,
            "case": 'lower',
        }
    },
    "resource": {
        "icon_cache_color": "#ffffff",
        "theme": "default.css"
    }
}


templates = {
    "General": {
        "Appearance": (
            {
                "desc": "Theme",
                "path": "resource::theme",
                "element": RadioGroup,
                "requires_restart": True,
                "extra": {
                    "choices": (
                        ("default.css", "Dark",),
                        ("light.css", "Light",),
                    )
                }
            },
        ),
        "Recent Files": (
            {
                "desc": "Recent files limit",
                "path": "studio::recent_max",
                "element": Number,
                "extra": {
                    "width": 4
                },
            },
            {
                "desc": "Show",
                "path": "studio::recent_show",
                "element": RadioGroup,
                "extra": {
                    "choices": (
                        ("name", "Only file name"),
                        ("path", "Full file path"),
                    )
                }
            },
            {
                "desc": "Maximum path display length",
                "path": "studio::recent_max_length",
                "element": Number,
                "extra": {
                    "width": 4
                },
            },
        ),
        "Undo Redo": (
            DependentGroup({
                "controller": {
                    "desc": "Limit undo depth",
                    "path": "studio::use_undo_depth",
                    "element": Check
                },
                "allow": [True, ],
                "children": (
                    {
                        "desc": "Undo depth",
                        "path": "studio::undo_depth",
                        "element": Number,
                        "extra": {
                            "width": 4,
                        }
                    },
                )
            }),
        ),
        "Start up": (
            {
                "desc": "At startup",
                "path": "studio::on_startup",
                "element": RadioGroup,
                "extra": {
                    "choices": (
                        ("new", "Open blank design tab"),
                        ("recent", "Restore previous tabs"),
                        ("blank", "Do not open any design tab")
                    )
                }
            },
        )
    },
    "Designer": {
        "Design pad": (
            {
                "desc": "Drag rate throttling",
                "path": "designer::frame_skip",
                "element": LabeledScale,
                "extra": {
                    "step": 1,
                    "_from": 1,
                    "to": 5,
                }
            },
        ),
        "Naming options": (
            {
                "desc": "Naming case",
                "path": "designer::label::case",
                "element": RadioGroup,
                "extra": {
                    "choices": (
                        ("title", "Title case (Button1, Label_1...)"),
                        ("lower", "Lower case (button2, label_2...)"),
                        ("upper", "Upper case (BUTTON2, LABEL2...)"),
                    )
                }
            },
            {
                "desc": "Use underscore separator",
                "path": "designer::label::underscore",
                "element": Check,
            },
{
                "desc": "Start numbering from",
                "path": "designer::label::start",
                "element": Number,
                "extra": {
                    "width": 4,
                    "values": (0, 1)
                },
            },
            {
                "element": Note,
                "desc": "(Widget names already created will not be affected)"
            },
        ),
        "Xml options": (
            {
                "desc": "Pretty print output xml",
                "path": "designer::xml::pretty_print",
                "element": Check,
            },
            {
                "element": Note,
                "desc": "(Requires lxml)"
            }
        ),
        "JSON options": (
            {
                "desc": "Compact output",
                "path": "designer::json::compact",
                "element": Check
            },
            {
                "desc": "Sort json keys",
                "path": "designer::json::sort_keys",
                "element": Check
            },
            {
                "desc": "Stringify json values",
                "path": "designer::json::stringify_values",
                "element": Check
            },
            DependentGroup({
                "controller": {
                    "desc": "Pretty print output json",
                    "path": "designer::json::pretty_print",
                    "element": Check
                },
                "allow": [True, ],
                "children": (
                    DependentGroup({
                        "controller": {
                            "desc": "For indentation use",
                            "path": "designer::json::indent",
                            "element": RadioGroup,
                            "extra": {
                                "choices": (
                                    ("\t", "Tabs"),
                                    ("", "Spaces")
                                ),
                                "tristatevalue": '-'
                            }
                        },
                        "allow": [""],
                        "children": (
                            {
                                "desc": "number of indent spaces",
                                "path": "designer::json::indent_count",
                                "element": Number,
                                "extra": {
                                    "width": 4
                                }
                            },
                        )
                    }),
                )
            })
        ),
        "Image options": (
            {
                "desc": "When selecting image",
                "path": "designer::image_path",
                "element": RadioGroup,
                "extra": {
                    "choices": (
                        ("mixed", "Use relative paths when in same directory as design file"),
                        ("relative", "Always use path relative to design file if possible"),
                        ("absolute", "Always use absolute paths")
                    )
                }
            },
            {
                "element": Note,
                "desc": "(Existing paths will not be affected, Reset the image to take effect)"
            }
        ),
        "Style pane options": (
            {
                "desc": "Use descriptive names for style attributes",
                "path": "designer::descriptive_names",
                "element": Check
            },
        )
    },
    "Key Map": {
        "_scroll": False,
        "hotkeys": {
            "layout": {
                "fill": "both",
                "expand": True,
            },
            "children": (
                DependentGroup({
                    "controller": {
                        "desc": "Allow shortcut keys",
                        "path": "allow_hotkeys",
                        "element": Check,
                    },
                    "allow": [True, ],  # Allow only when controller value is True
                    "children": (
                        {
                            "desc": "Configure shortcut keys",
                            "path": "hotkeys",
                            "element": ShortcutPane,
                            "layout": {
                                "fill": "both",
                                "expand": True,
                                "padx": 5,
                                "pady": 5
                            }
                        },
                    )
                }),
            )
        }
    }
}

class Preferences(SharedPreferences):

    @classmethod
    def acquire(cls):
        return cls("formation", "hoverset", "config", defaults)

    def update_recent(self, path):
        if not path:
            return
        recent = self.get("studio::recent")
        max_recent = self.get("studio::recent_max")
        if not os.path.exists(path):
            # path doesn't exist just remove it
            recent.remove(path)
            return
        if path in recent:
            recent.remove(path)
        recent = recent[:max_recent - 1]
        recent.insert(0, path)
        self.set("studio::recent", recent)

    def truncate_label(self, label):
        maximum = self.get("studio::recent_max_length")
        excess = len(label) - maximum
        if excess <= 0:
            return label

        # remove space required by ellipsis which is 3 characters
        trail = (maximum - 3) // 2
        return f"{label[:trail]}...{label[-trail:]}"

    def get_recent_label(self, path):
        show = self.get("studio::recent_show")
        label = path if show == "path" else os.path.basename(path)
        return self.truncate_label(label)

    def get_recent(self):
        recent = self.get("studio::recent")[:self.get("studio::recent_max")]
        return [(path, self.get_recent_label(path)) for path in recent]

    def clear_recent(self):
        self.set("studio::recent", [])  # clear recent files

    def get_latest(self):
        if self.get("studio::recent"):
            return self.get("studio::recent")[0]
        return None


def open_preferences(master):
    PreferenceManager(master, Preferences.acquire(), templates)


def get_active_pref(widget):
    import hoverset.ui.widgets as widgets
    if hasattr(widget, 'window') and hasattr(widget.window, 'pref'):
        return widget.window.pref
    else:
        check = widget.master
        while not (isinstance(check, widgets.Application) or check is None):
            check = check.master
        if hasattr(check, 'pref'):
            return check.pref

    logger.error("Unable to acquire context sensitive preference")
    return None
