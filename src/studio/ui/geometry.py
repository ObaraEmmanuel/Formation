"""
Helper geometry functionality. The following terms will be used:

    1. ``bound``: refers to a tuple with coordinates of top left and
       bottom right corners of a screen section i.e. ``(x1, y1, x2, y2)``.
       It may be shortened to ``bd``
    2. ``dimension``: used to refer to top left corner and width/height
       of a screen section i.e. ``(x, y, width, height)``
    3. ``position`` is used to refer to a single point on screen
       i.e. ``(x, y)``.

The following modifiers may be used together with the terms described above:

    * **absolute**: Relative to the entire screen
    * **relative**: Relative to a widget or toplevel window

"""

# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #


def bounds(widget):
    """
    Get bounding box of widget relative to its parent

    :param widget: widget whose bounds are to be determined
    :return: bound tuple ``(x1, y1, x2, y2)`` representing position
        of widget within its parent
    """
    widget.update_idletasks()
    return (widget.winfo_x(), widget.winfo_y(),
            widget.winfo_x() + widget.winfo_width(), widget.winfo_y() + widget.winfo_height())


def absolute_position(widget):
    """
    Get dimension of widget relative to the whole screen

    :param widget: widget whose bounds are to be determined
    :return: absolute dimension tuple ``(x, y, width, height)``
    """
    widget.update_idletasks()
    return widget.winfo_rootx(), widget.winfo_rooty(), widget.winfo_width(), widget.winfo_height()


def absolute_bounds(widget):
    """
    Get bounds of widget relative to the whole screen

    :param widget: widget whose bounds are to be determined
    :return: absolute bound tuple ``(x1, y1, x2, y2)``
    """
    x = widget.winfo_rootx()
    y = widget.winfo_rooty()
    return x, y, x + widget.winfo_width(), y + widget.winfo_height()


def resolve_bounds(bd, widget):
    """
    Convert bounds ``bd`` to be relative to the absolute bound of ``widget``

    :param bd: bounds to be converted
    :param widget: Widget to which bounds are to be relative to
    :return: resolved bound tuple
    """
    ref = absolute_bounds(widget)
    return bd[0] - ref[0], bd[1] - ref[1], bd[2] - ref[0], bd[3] - ref[1]


def relative_bounds(bd, widget):
    """
    Convert bounds ``bd`` to be relative to the relative bound of ``widget``

    :param bd: bounds to be converted
    :param widget: Widget to which bounds are to be relative to
    :return: relative bound tuple
    """
    ref = bounds(widget)
    return bd[0] - ref[0], bd[1] - ref[1], bd[2] - ref[0], bd[3] - ref[1]


def resolve_position(position, widget):
    """
    Convert an absolute position such that it is relative to a ``widget``

    :param position: absolute position ``(x, y)`` to be resolved
    :param widget: widget to which position is to be made relative
    :return: position ``(x, y)`` resolved to be relative to ``widget``
    """
    return position[0] - widget.winfo_rootx(), position[1] - widget.winfo_rooty()


def compute_overlap(bound1, bound2):
    """
    Get the bound of the overlapping section between two bounds

    :param bound1: bound where overlap is to be checked
    :param bound2: bound where overlap is to be checked
    :return: bound tuple of overlap between ``bound1`` and ``bound2``
        if there is no overlap ``None`` is returned
    """
    ax1, ay1, ax2, ay2 = bound1
    bx1, by1, bx2, by2 = bound2

    ox1, oy1, ox2, oy2 = max(ax1, bx1), max(ay1, by1), min(ax2, bx2), min(ay2, by2)
    if ox1 < ox2 and oy1 < oy2:
        return ox1, oy1, ox2, oy2
    else:
        return None


def upscale_bounds(bound, widget):
    """
    Convert bounds to be relative to a higher level ``widget`` i.e scale up

    :param bound: relative bounds to be up-scaled
    :param widget: A higher level widget to which bounds are to be relative
    :return:
    """
    ref = bounds(widget)
    x_offset, y_offset = ref[0], ref[1]
    return bound[0] + x_offset, bound[1] + y_offset, bound[2] + x_offset, bound[3] + y_offset


def center(bound):
    """
    Get the coordinates of the center of a bound

    :param bound: a bound tuple
    :return: integer coordinates of center as a tuple ``(x, y)``
    """
    return (bound[2] - bound[0]) // 2, (bound[3] - bound[1]) // 2


def is_within(bound1, bound2) -> bool:
    """
    Checks whether bound2 is within bound1 i.e bound1 completely encloses bound2

    :param bound1: A tuple, The enclosing bound
    :param bound2: A tuple, The enclosed bound
    :return: ``True`` if ``bound1`` encloses ``bound2`` else ``False``
    """
    overlap = compute_overlap(bound1, bound2)
    if overlap == bound2:
        return True
    return False


def dimensions(bound):
    """
    Get the width and height of a bound

    :param bound: a bound tuple
    :return: a tuple containing the width and height of the ``bound``
        i.e ``(width, height)``
    """
    return bound[2] - bound[0], bound[3] - bound[1]


def make_event_relative(event, relative_to):
    """
    Change the event object's ``x`` and ``y`` attributes such that
    they are relative to ``relative_to`` parameter

    :param event: tk event to be modified
    :param relative_to: The widget to which the event is to be made relative to
    :return: None
    """
    event.x = event.x_root - relative_to.winfo_rootx()
    event.y = event.y_root - relative_to.winfo_rooty()


def dimension_to_bounds(x, y, width, height):
    """
    Convert a positioned rectangular section into a bounding box coordinates
    indicating the top left and bottom right.

    :param x: x position or rectangular section
    :param y: y position or rectangular section
    :param width: width of section
    :param height: height of section
    :return: a tuple representing the top left and bottom right corners
        (x1, y1, x2, y2)
    """
    return x, y, x + width, y + height
