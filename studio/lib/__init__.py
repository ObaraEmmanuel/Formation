from collections import defaultdict


class NameGenerator:

    def __init__(self, pref):
        self.pref = pref
        self._ids = defaultdict(lambda: int(pref.get("designer::label::start")))

    def _make_name(self, name):
        use_ = self.pref.get("designer::label::underscore")
        case = self.pref.get("designer::label::case")
        prefix = name
        if case == 'title':
            prefix = name.title()
        elif case == 'lower':
            prefix = name.lower()
        elif case == 'upper':
            prefix = name.upper()

        return f"{prefix}{'_' if use_ else ''}{self._ids[name]}"

    def generate(self, obj_class, lookup=None):
        """
            Unified unique id generator. Increments id count for different object
            types and hopefully returns a unique id

            :param obj_class: object class preferably with a ``display_name`` attribute
            :param lookup: An iterable with which to enforce uniqueness. IDs generated
                will not be duplicates if IDs present in lookup. If not provided
                uniqueness is not guaranteed.
            """
        if hasattr(obj_class, "display_name"):
            name = obj_class.display_name
        else:
            name = obj_class.__name__

        _ids = self._ids

        _id = self._make_name(name)
        _ids[name] += 1

        if lookup:
            while _id in lookup:
                _id = self._make_name(name)
                _ids[name] += 1

        return _id
