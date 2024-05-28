# ======================================================================= #
# Copyright (C) 2022 Hoverset Group.                                      #
# ======================================================================= #
import tkinter as tk


def is_class_toplevel(cls):
    if cls in (tk.Toplevel, tk.Tk):
        return True
    for base in cls.__bases__:
        if is_class_toplevel(base):
            return True
    return False


def is_class_root(cls):
    if cls == tk.Tk:
        return True
    for base in cls.__bases__:
        if is_class_root(base):
            return True
    return False


class CustomPropertyMixin:
    """
    Simplifies addition of custom properties to tkinter widgets.
    By using a simple definition of the properties in the ``prop_info``
    class attribute, it allows you to access and modify custom properties as
    though they were built-in tkinter properties. To define a property,
    you need to specify the following attributes

        * name : The name of the custom attribute. Should be the same as the
          key of the property in the ``prop_info`` dictionary
        * default: The default value of the custom attribute
        * setter: name of the method used to set the property as a string.
          the setter should accept one argument which is the value being set
        * getter: name of the attribute used to store the property.

    .. note::
        It is upto you to store the custom attribute values and provide them
        on demand in the getter. Ensure the getter contains the most upto-date
        value.

    .. code-block:: python

        class MyCustomWidget(CustomPropertyMixin, tkinter.Frame):

            prop_info = {
                "background_image": {
                    "name": "background_image",
                    "default": None,
                    "setter": "set_background_img",
                    "getter": "bg_img"
                },
                "title_text": {
                    "name": "title_text",
                    "default": "",
                    "setter": "set_title",
                    "getter": "title"
                },
            }

            def __init__(master=None, **kw):
                # do not pass kw directly to super call
                super().__init__(master)
                self.title = ""
                self.bg_img = None

                # should be the last thing
                self.configure(kw)

            def set_background_img(self, value):
                self.bg_img = value
                # extra logic to apply attribute

            def set_title(self, value):
                self.title = value
                # extra logic to apply attribute

    The custom widget can then be used as shown below:

    .. code-block:: python

        >>> widget = MyCustomWidget(parent)
        >>> widget.config(title_text="my title", bg="red", background_image=img)
        >>> print(widget["title_text"])
        my_title
        >>> print(widget.cget("title_text"))
        my_title
        >>> widget["title_text"] = "new title"
        >>> print(widget["title_text"])
        new_title


    """
    prop_info = {}

    def _resolve_getter(self, prop):
        val = getattr(self, prop)
        return val if not callable(val) else val()

    def configure(self, cnf=None, **kw):
        if isinstance(cnf, str):
            if cnf in self.prop_info:
                p = self.prop_info[cnf]
                return (
                    p["name"], p["name"], p["name"].title(),
                    p["default"],
                    self._resolve_getter(p["getter"]),
                )
            else:
                return super().configure(cnf)

        if cnf is None and not kw:
            cnf = super().configure() or {}
            prp = self.prop_info.values()
            cnf.update({p["name"]: (
                p["name"], p["name"], p["name"].title(),
                p["default"],
                self._resolve_getter(p["getter"])) for p in prp})
            return cnf

        cnf = cnf or {}
        cnf.update(kw)
        customs = cnf.keys() & self.prop_info.keys()
        for key in customs:
            getattr(self, self.prop_info[key]["setter"])(cnf.pop(key))
        super().configure(**cnf)

    config = configure

    def keys(self):
        keys = super().keys()
        keys.extend(self.prop_info.keys())
        return keys

    def cget(self, key):
        if key in self.prop_info:
            return self._resolve_getter(self.prop_info[key]["getter"])
        return super().cget(key)

    __getitem__ = cget

    def __setitem__(self, key, value):
        if key in self.prop_info:
            getattr(self, self.prop_info[key]["setter"])(value)
        else:
            super().__setitem__(key, value)

def callback_parse_helper(*args, **kwargs):
        return args, kwargs
    
def callback_parse(command:str):
    """
    ## Added in Issue #32: https://github.com/ObaraEmmanuel/Formation/issues/32
    
    Returns parts of a command after parsing it using eval method.

    Args:
        ``command (str): . . `` command string.
    
    Command String Syntax:
    	``funcname 1 "arg2",kwarg1="hello",kwarg2="world!"``

    Returns:
        ``command_func (str) : . . . . ``name of the function.
        ``command_args (list): . . . . ``values of regular arguments.
        ``command_kwargs (dict): . . . ``values of kwargs.
    """

    command_list:list = command.split(' ')
    command_func: str = command_list[0]
    command_list.pop(0)
    command_string = ""
    for arg in command_list:
        command_string+=(arg+' ')
    command_string.removesuffix(' ')
    args, kwargs = eval(f'callback_parse_helper({command_string})')
    return command_func, args, kwargs

# if __name__ == "__main__":
#     command = "btn 1, 2, 3, 'hello this is a world!', kw1='my kwarg'"
#     output = parse(command)
#     command_func, command_args, command_kwargs = output
#     print(f"{command_kwargs = }")
#     print(f"{command_args = }")
#     print(f"{command_func = }")

