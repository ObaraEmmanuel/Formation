from collections import namedtuple

count = 0
EventBinding = namedtuple("EventBinding", ["id", "sequence", "handler", "add"])


def make_event(sequence, handler, add):
    return EventBinding(generate_id(), sequence, handler, add)


def generate_id():
    global count
    _id = count
    count += 1
    return _id
