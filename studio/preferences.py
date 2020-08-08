from hoverset.data.preferences import SharedPreferences

defaults = {
    "studio": {
        "recent": [],
        "recent_max": 20,
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
        }
    },
    "features": {},
}


class Preferences(SharedPreferences):

    @classmethod
    def acquire(cls):
        return cls("formation", "hoverset", "config", defaults)
