from PIL import Image, ImageTk


def load_image(path, builder):
    # load image at path
    image = Image.open(path)
    image = ImageTk.PhotoImage(image=image)
    builder._image_cache.append(image)
    return image


def load_variable(variable, builder):
    # find the variable which will be preloaded on the builder
    return getattr(builder, variable, '')


# any properties requiring special pre-processing go here
_preprocess = {
    "image": load_image,
    "selectimage": load_image,
    "tristateimage": load_image,
    "textvariable": load_variable,
    "variable": load_variable,
    "listvariable": load_variable
}


def preprocess(builder, options):
    """
    Preprocess attributes which can not be assigned to widgets directly like
    images and variables.
    :param builder: Builder object as provided by the loader
    :param options: a dictionary of unprocessed attributes
    :return: dictionary of processed attribute values
    """
    for opt in options:
        if opt in _preprocess:
            # requires pre-processing
            options[opt] = _preprocess[opt](options[opt], builder)
    return options
