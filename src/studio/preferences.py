import os

from hoverset.data.preferences import *
from hoverset.data.keymap import ShortcutPane
from hoverset.data.utils import get_resource_path

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
            "x": 0,
            "y": 0,
            "width": 200,
            "height": 200,
            "state": 'zoomed'
        },
        "on_startup": "new",
        "smoothness": 3,
    },
    "features": {},
    "hotkeys": {},
    "designer": {
        "frame_skip": 4,
        "xml": {
            "pretty_print": True,
        }
    },
    "resource": {
        "icon_cache_color": "#ffffff",
        "theme": get_resource_path("hoverset.ui", "themes/default.css")
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
                        (get_resource_path("hoverset.ui", "themes/default.css"), "Dark", ),
                        (get_resource_path("hoverset.ui", "themes/light.css"), "Light", ),
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
        "Start up": (
            {
                "desc": "At startup",
                "path": "studio::on_startup",
                "element": RadioGroup,
                "extra": {
                    "choices": (
                        ("new", "Open new design file"),
                        ("recent", "Open most recent design file"),
                        ("blank", "Do not open any design")
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
        "Xml options": (
            {
                "desc": "Pretty print output xml",
                "path": "designer::xml::pretty_print",
                "element": Check,
            },
        )
    },
    "Key Map": {
        "hotkeys": DependentGroup({
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
        })
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
        if len(self.get("studio::recent")):
            return self.get("studio::recent")[0]
        return None


def open_preferences(master):
    PreferenceManager(master, Preferences.acquire(), templates)
