from collections import defaultdict


_ids = defaultdict(int)


def generate_id(obj_class, lookup=None):
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

    _ids[name] += 1
    _id = f"{name}_{_ids[name]}"

    if lookup:
        while _id in lookup:
            _ids[name] += 1
            _id = f"{name}_{_ids[name]}"

    return _id
