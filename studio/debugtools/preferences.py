from hoverset.data.preferences import *
import studio.preferences

defaults = {
    "debugger": {
        "geometry": "400x500",
    },
    "resource": studio.preferences.defaults["resource"],
}


class Preferences(SharedPreferences):

    @classmethod
    def acquire(cls):
        return cls("formation-debugger", "hoverset", "config", defaults)
