from hoverset.data.preferences import *
import studio.preferences

defaults = {
    "debugger": {
        "geometry": "400x800",
    },
    "resource": studio.preferences.defaults["resource"],
    "console": {
        "history_max": 1000,
        "history": []
    },
    "locale": {
        "language": "en"
    }
}


class Preferences(SharedPreferences):

    @classmethod
    def acquire(cls):
        return cls("formation-debugger", "hoverset", "config", defaults)

    def update_console_history(self, command):
        history = self.get("console::history")
        max_hist = self.get("console::history_max")
        if command in history:
            history.remove(command)

        history = history[: max_hist - 1]
        history.insert(0, command)
        self.set("console::history", history)
