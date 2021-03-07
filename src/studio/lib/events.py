from collections import namedtuple

count = 0
EventBinding = namedtuple("EventBinding", ["id", "sequence", "handler", "add"])


def make_event(*args, **kwargs):
    return EventBinding(generate_id(), *args, **kwargs)


def generate_id():
    global count
    _id = count
    count += 1
    return _id
