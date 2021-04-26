import itertools
import math
import os
import pathlib

from PIL import ImageTk, Image


def to_tk_image(image):
    return ImageTk.PhotoImage(image)


def get_frames(image):
    # Get all frames present in an image
    frames = [to_tk_image(image)]
    try:
        while True:
            image.seek(image.tell() + 1)
            frames.append(to_tk_image(image))
    except EOFError:
        pass
    return frames


def load_image_to_widget(widget, image, prop, builder, handle_method=None):
    # cancel any animate cycles present
    cycle_attr = '_{}_cycle'.format(prop)
    handle_method = widget.config if handle_method is None else handle_method
    if hasattr(widget, cycle_attr):
        widget.after_cancel(getattr(widget, cycle_attr))
    if not isinstance(image, Image.Image):
        # load non PIL image values
        handle_method(**{prop: image})
        # store a reference to shield from garbage collection
        builder._image_cache.append(image)
        return
    if not hasattr(image, "is_animated") or not image.is_animated:
        image = to_tk_image(image)
        handle_method(**{prop: image})
        # store a reference to shield from garbage collection
        builder._image_cache.append(image)
        return
    # Animate the image only if there are more than one frames
    frames = get_frames(image)
    frame_count = len(frames)
    if frame_count == 1:
        handle_method(**{prop: frames[0]})
        return

    # an infinite iterator to loop through the frames continuously
    cycle = itertools.cycle(frames)
    loop = image.info.get("loop", 0)
    loop = math.inf if loop == 0 else loop
    loop_count = 0

    def cycle_frames():
        nonlocal loop_count
        handle_method(**{prop: next(cycle)})
        loop_count += 1
        if loop_count // frame_count >= loop:
            return
        setattr(widget, cycle_attr, widget.after(image.info.get("duration", 100), cycle_frames))

    # begin animation
    cycle_frames()


def handle(widget, config, **kwargs):
    props = kwargs.get("extra_config", {})
    handle_method = kwargs.get("handle_method")
    builder = kwargs.get("builder")
    for prop in props:
        path = pathlib.Path(props[prop])
        if not path.is_absolute() and builder.path is not None:
            path = pathlib.Path(os.path.dirname(builder.path), path)
        image = Image.open(path)
        load_image_to_widget(widget, image, prop, builder, handle_method)
