from collections import namedtuple

count = 0
EventBinding = namedtuple("EventBinding", ["id", "sequence", "handler", "add"])


def event_equal(event1, event2):
    return event1.sequence == event2.sequence and event1.handler == event2.handler and event1.add == event2.add


def make_event(*args, **kwargs):
    return EventBinding(generate_id(), *args, **kwargs)


def generate_id():
    global count
    _id = count
    count += 1
    return _id
