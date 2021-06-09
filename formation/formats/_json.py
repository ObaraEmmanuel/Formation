from formation.formats._base import BaseFormat


class JSONFormat(BaseFormat):
    extensions = ["json"]
    name = "JSON"

    def load(self):
        pass

    def generate(self, **kw):
        pass
