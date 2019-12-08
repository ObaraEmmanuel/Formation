"""
Helper geometry functionality
"""


# ======================================================================= #
# Copyright (C) 2019 Hoverset Group.                                      #
# ======================================================================= #


def bounds(widget):
    widget.update_idletasks()
    return (widget.winfo_x(), widget.winfo_y(),
            widget.winfo_x() + widget.winfo_width(), widget.winfo_y() + widget.winfo_height())


def absolute_bounds(widget):
    x = widget.winfo_rootx() - widget.window.winfo_rootx()
    y = widget.winfo_rooty() - widget.window.winfo_rooty()
    return x, y, x + widget.winfo_width(), y + widget.winfo_height()


def resolve_bounds(bd, widget):
    ref = absolute_bounds(widget)
    return bd[0] - ref[0], bd[1] - ref[1], bd[2] - ref[0], bd[3] - ref[1]


def relative_bounds(bd, widget):
    ref = bounds(widget)
    return bd[0] - ref[0], bd[1] - ref[1], bd[2] - ref[0], bd[3] - ref[1]


def resolve_position(position, widget):
    return position[0] - widget.winfo_rootx(), position[1] - widget.winfo_rooty()


def compute_overlap(bound1, bound2):
    ax1, ay1, ax2, ay2 = bound1
    bx1, by1, bx2, by2 = bound2

    ox1, oy1, ox2, oy2 = max(ax1, bx1), max(ay1, by1), min(ax2, bx2), min(ay2, by2)
    if ox1 < ox2 and oy1 < oy2:
        return ox1, oy1, ox2, oy2
    else:
        return None


def is_within(bound1, bound2) -> bool:
    """
    Checks whether bound2 is within bound1 i.e bound1 completely encloses bound2
    :param bound1: A tuple, The enclosing bound
    :param bound2: A tuple, The enclosed bound
    :return: bool True if bound1 encloses bound2 else False
    """
    overlap = compute_overlap(bound1, bound2)
    if overlap == bound2:
        return True
    return False
