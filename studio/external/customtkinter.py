import tkinter
from studio.external._base import FeatureNotAvailableError

try:
    import customtkinter
except (ModuleNotFoundError, ImportError):
    raise FeatureNotAvailableError()

from formation.utils import CustomPropertyMixin
from studio import WidgetMeta
from studio.lib.toplevel import _Toplevel
from studio.feature.components import ComponentPane, ComponentGroup


def color_compose():
    return [
        [
            {
                "display_name": "light",
                "name": "light",
                "type": "color",
            },
            {
                "display_name": "dark",
                "name": "dark",
                "type": "color",
            }
        ]
    ]


CTK_PROPERTIES = {
    "activate_scrollbars": {
        "display_name": "activate scrollbars",
        "type": "bool",
        "default": True
    },
    "anchor": {
        "display_name": "anchor",
        "type": "anchor",
        "multiple": False,
        "default": "center"
    },
    "border_color": {
        "display_name": "border color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "border_spacing": {
        "display_name": "border spacing",
        "type": "dimension",
        "default": 2
    },
    "border_width": {
        "display_name": "border width",
        "type": "dimension",
        "default": 0
    },
    "border_width_checked": {
        "display_name": "border width checked",
        "type": "dimension"
    },
    "border_width_unchecked": {
        "display_name": "border width unchecked",
        "type": "dimension"
    },
    "button_color": {
        "display_name": "button color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "button_hover_color": {
        "display_name": "button hover color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "checkbox_height": {
        "display_name": "checkbox height",
        "type": "dimension"
    },
    "checkbox_width": {
        "display_name": "checkbox width",
        "type": "dimension"
    },
    "command": {
        "display_name": "command",
        "type": "command"
    },
    "compound": {
        "display_name": "compound",
        "type": "choice",
        "choices": [
            "top",
            "left",
            "bottom",
            "right"
        ],
        "default": "left"
    },
    "corner_radius": {
        "display_name": "corner radius",
        "type": "dimension"
    },
    "determinate_speed": {
        "display_name": "determinate speed",
        "type": "text",
        "default": 1
    },
    "dropdown_fg_color": {
        "display_name": "dropdown fg color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "dropdown_font": {
        "display_name": "dropdown font",
        "type": "font"
    },
    "dropdown_hover_color": {
        "display_name": "dropdown hover color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "dropdown_text_color": {
        "display_name": "dropdown text color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "dynamic_resizing": {
        "display_name": "dynamic resizing",
        "type": "bool",
        "default": True
    },
    "fg_color": {
        "display_name": "forground color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "font": {
        "display_name": "font",
        "type": "font",
        "string_output": False
    },
    "from_": {
        "display_name": "from",
        "type": "number"
    },
    "height": {
        "display_name": "height",
        "type": "dimension"
    },
    "hover": {
        "display_name": "hover",
        "type": "bool",
        "default": True
    },
    "hover_color": {
        "display_name": "hover color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "image": {
        "display_name": "image",
        "type": "image"
    },
    "indeterminate_speed": {
        "display_name": "indeterminate speed",
        "type": "text",
        "default": 1
    },
    "justify": {
        "display_name": "justify",
        "type": "choice",
        "options": [
            "left",
            "center",
            "right"
        ],
        "default": "center"
    },
    "label_anchor": {
        "display_name": "label anchor",
        "type": "anchor",
        "multiple": False,
        "default": "center"
    },
    "label_fg_color": {
        "display_name": "label fg color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "label_font": {
        "display_name": "label font",
        "type": "font",
        "string_output": False
    },
    "label_text": {
        "display_name": "label text",
        "type": "text"
    },
    "label_text_color": {
        "display_name": "label text color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "minimum_pixel_length": {
        "display_name": "minimum pixel length",
        "type": "dimension"
    },
    "mode": {
        "display_name": "mode",
        "type": "choice",
        "choices": [
            "determinate",
            "indeterminate"
        ],
        "default": "determinate"
    },
    "number_of_steps": {
        "display_name": "number of steps",
        "type": "number"
    },
    "offvalue": {
        "display_name": "off value",
        "type": "text"
    },
    "onvalue": {
        "display_name": "on value",
        "type": "text"
    },
    "orientation": {
        "display_name": "orientation",
        "type": "choice",
        "choices": [
            "horizontal",
            "vertical"
        ],
        "default": "horizontal"
    },
    "placeholder_text": {
        "display_name": "placeholder text",
        "type": "text"
    },
    "placeholder_text_color": {
        "display_name": "placeholder text color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "progress_color": {
        "display_name": "progress color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "radiobutton_height": {
        "display_name": "radiobutton height",
        "type": "dimension"
    },
    "radiobutton_width": {
        "display_name": "radiobutton width",
        "type": "dimension"
    },
    "scrollbar_button_color": {
        "display_name": "scrollbar button color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "scrollbar_button_hover_color": {
        "display_name": "scrollbar button hover color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "scrollbar_fg": {
        "display_name": "scrollbar fg",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "scrollbar_fg_color": {
        "display_name": "scrollbar fg color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "segmented_button_fg_color": {
        "display_name": "segmented button fg color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "segmented_button_selected_color": {
        "display_name": "segmented button selected color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "segmented_button_selected_hover_color": {
        "display_name": "segmented button selected hover color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "segmented_button_unselected_color": {
        "display_name": "segmented button unselected color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "segmented_button_unselected_hover_color": {
        "display_name": "segmented button unselected hover color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "selected_color": {
        "display_name": "selected color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "selected_hover_color": {
        "display_name": "selected hover color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "state": {
        "display_name": "state",
        "type": "choice",
        "choices": [
            "normal",
            "disabled"
        ],
        "default": "normal"
    },
    "switch_height": {
        "display_name": "switch height",
        "type": "dimension"
    },
    "switch_width": {
        "display_name": "switch width",
        "type": "dimension"
    },
    "text_color": {
        "display_name": "text color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "text_color_disabled": {
        "display_name": "text color disabled",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "textvariable": {
        "display_name": "text variable",
        "type": "variable"
    },
    "to": {
        "display_name": "to",
        "type": "number"
    },
    "unselected_color": {
        "display_name": "unselected color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "unselected_hover_color": {
        "display_name": "unselected hover color",
        "type": "compose",
        "as_dict": False,
        "compose": color_compose()
    },
    "value": {
        "display_name": "value",
        "type": "text"
    },
    "values": {
        "display_name": "values",
        "type": "text"
    },
    "variable": {
        "display_name": "variable",
        "type": "variable"
    },
    "width": {
        "display_name": "width",
        "type": "dimension"
    }
}


def with_name(properties):
    return {
        k: {"name": k, **v}
        for k, v in properties.items()
    }


_common_keys = (
    "width",
    "height",
    "corner_radius",
    "fg_color"
)

# Patch out irritating imaging warnings
customtkinter.CTkBaseClass._check_image_type = lambda self, image: image


class CustomTkMixin:
    """Work-arounds for broken custom tkinter API"""

    def patch_setter_getter(self):
        for k in self._keys:
            setattr(self, f"_ext_set_{k}", self._make_setter(k))
            setattr(self, f"_ext_{k}", self._make_getter(k))

    def _make_setter(self, prop):
        return lambda val: self._ext_configure(**{prop: val})

    def _make_getter(self, prop):
        return lambda: self._ext_cget(prop)

    def place(self, **kw):
        conf = {}
        if "width" in kw:
            conf["width"] = int(kw.pop("width"))
        if "height" in kw:
            conf["height"] = int(kw.pop("height"))
        super().configure(**conf)
        super().place(**kw)
        # we'll still have to bypass crappy customtkinter place handling
        return tkinter.Widget.place(self, **kw, **conf)

    def place_configure(self, **kw):
        if "width" in kw:
            self._ext_set_width(int(kw.get("width")))
        if "height" in kw:
            self._ext_set_height(int(kw.get("height")))
        return super().place_configure(**kw)

    def place_info(self):
        info = super().place_info()
        info.pop("width", None)
        info.pop("height", None)
        return info

    def _ext_configure(self, **kw):
        for prop in kw:
            prop_def = CTK_PROPERTIES.get(prop, {})
            if prop_def.get("type") == "compose" and isinstance(kw[prop], str) and " " in kw[prop]:
                kw[prop] = kw[prop].split(" ")
            if prop_def.get("type") == "compose" and isinstance(kw[prop], (list, tuple)):
                if 'transparent' in kw[prop]:
                    kw[prop] = 'transparent'
            if prop_def.get("type") == "dimension" and isinstance(kw[prop], str):
                kw[prop] = int(kw[prop])
            if prop_def.get("type") == "font" and isinstance(kw[prop], list):
                kw[prop] = tuple(kw[prop])
        return self.klass.configure(self, **kw)

    def _ext_cget(self, prop):
        try:
            val = self.klass.cget(self, prop)
        except Exception as e:
            val = getattr(self, f"_{prop}", '')

        if isinstance(val, customtkinter.CTkFont):
            return self._font_to_tuple(val)
        return val

    def _font_to_tuple(self, font):
        val = [font["family"], font["size"]]
        if font["weight"] != "normal":
            val.append(font["weight"])
        if font["slant"] != "roman":
            val.append(font["slant"])
        if font["underline"] == "underline":
            val.append("underline")
        if font["overstrike"] == "overstrike":
            val.append("overstrike")
        return tuple(val)

    def bind(self, sequence=None, func=None, add=None):
        return super().bind(sequence, func, "+")


class BindBypassMixin:

    def bind(self, sequence=None, func=None, add=None):
        return tkinter.Misc.bind(self, sequence, func, add)

    def unbind(self, sequence=None, funcid=None):
        return tkinter.Misc.unbind(self, sequence, funcid)


class CTkButton(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkButton):
    _keys = (
        *_common_keys,
        "border_width",
        "border_spacing",
        "hover_color",
        "border_color",
        "text_color",
        "text_color_disabled",
        "text",
        "font",
        "textvariable",
        "image",
        "state",
        "hover",
        "command",
        "compound",
        "anchor"
    )

    klass = customtkinter.CTkButton

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


class CTkButtonMeta(CTkButton, metaclass=WidgetMeta):
    display_name = "CTkButton"
    is_container = False
    icon = "button"
    impl = customtkinter.CTkButton
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)


class CTkLabel(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkLabel):
    _keys = (
        *_common_keys,
        "text_color",
        "text",
        "font",
        "textvariable",
        "anchor",
        "compound",
        "justify",
        "padx",
        "pady",
        "cursor",
        "image",
        "state",
        "takefocus",
        "underline",
        "wraplength",
    )

    klass = customtkinter.CTkLabel

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


class CTkLabelMeta(CTkLabel, metaclass=WidgetMeta):
    display_name = "CTkLabel"
    is_container = False
    icon = "label"
    impl = customtkinter.CTkLabel
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)


class CTkEntry(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkEntry):
    _keys = (
        *_common_keys,
        "text_color",
        "placeholder_text_color",
        "placeholder_text",
        "font",
        "state",
        "textvariable",
        "exportselection",
        "insertborderwidth",
        "insertofftime",
        "insertontime",
        "insertwidth",
        "justify",
        "selectborderwidth",
        "show",
        "takefocus",
        "validate",
        "validatecommand",
        "xscrollcommand"
    )

    klass = customtkinter.CTkEntry

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


class CTkEntryMeta(CTkEntry, metaclass=WidgetMeta):
    display_name = "CTkEntry"
    is_container = False
    icon = "entry"
    impl = customtkinter.CTkEntry
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)
    allow_direct_move = False


class CTkCheckBox(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkCheckBox):
    _keys = (
        *_common_keys,
        "checkbox_width",
        "checkbox_height",
        "border_width",
        "border_color",
        "hover_color",
        "text_color",
        "text_color_disabled",
        "text",
        "font",
        "hover",
        "state",
        "command",
        "variable",
        # "onvalue",
        # "offvalue",
    )

    klass = customtkinter.CTkCheckBox

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


class CTkCheckBoxMeta(CTkCheckBox, metaclass=WidgetMeta):
    display_name = "CTkCheckBox"
    is_container = False
    icon = "checkbox"
    impl = customtkinter.CTkCheckBox
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)


class CTkComboBox(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkComboBox):
    _keys = (
        *_common_keys,
        "border_width",
        "border_color",
        "button_color",
        "button_hover_color",
        "dropdown_fg_color",
        "dropdown_hover_color",
        "dropdown_text_color",
        "text_color",
        "text_color_disabled",
        "font",
        "dropdown_font",
        "values",
        "hover",
        "state",
        "command",
        "variable",
        "justify",
    )

    klass = customtkinter.CTkComboBox

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


class CTkComboBoxMeta(CTkComboBox, metaclass=WidgetMeta):
    display_name = "CTkComboBox"
    is_container = False
    icon = "menubutton"
    impl = customtkinter.CTkComboBox
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)
    allow_direct_move = False


class CTkFrame(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkFrame):
    _keys = (
        *_common_keys,
        "border_width",
        "border_color",
    )

    klass = customtkinter.CTkFrame

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


class CTkFrameMeta(CTkFrame, metaclass=WidgetMeta):
    display_name = "CTkFrame"
    is_container = True
    icon = "frame"
    impl = customtkinter.CTkFrame
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)


class CTkOptionMenu(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkOptionMenu):
    _keys = (
        *_common_keys,
        "button_color",
        "button_hover_color",
        "dropdown_fg_color",
        "dropdown_hover_color",
        "dropdown_text_color",
        "text_color",
        "text_color_disabled",
        "font",
        "dropdown_font",
        "hover",
        "state",
        "command",
        "variable",
        "values",
        "anchor",
        "dynamic_resizing",
    )

    klass = customtkinter.CTkOptionMenu

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


class CTkOptionMenuMeta(CTkOptionMenu, metaclass=WidgetMeta):
    display_name = "CTkOptionMenu"
    is_container = False
    icon = "menubutton"
    impl = customtkinter.CTkOptionMenu
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)
    allow_direct_move = False


class CTkProgressBar(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkProgressBar):
    _keys = (
        *_common_keys,
        "border_width",
        "border_color",
        "progress_color",
        "orientation",
        "mode",
        "determinate_speed",
        "indeterminate_speed",
    )

    klass = customtkinter.CTkProgressBar

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


class CTkProgressBarMeta(CTkProgressBar, metaclass=WidgetMeta):
    display_name = "CTkProgressBar"
    is_container = False
    icon = "progressbar"
    impl = customtkinter.CTkProgressBar
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)


class CTkRadioButton(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkRadioButton):
    _keys = (
        *_common_keys,
        "radiobutton_width",
        "radiobutton_height",
        "border_width_unchecked",
        "border_width_checked",
        "border_color",
        "hover_color",
        "text_color",
        "text_color_disabled",
        "text",
        "font",
        "hover",
        "state",
        "command",
        "variable",
        # "value",
    )

    klass = customtkinter.CTkRadioButton

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


class CTkRadioButtonMeta(CTkRadioButton, metaclass=WidgetMeta):
    display_name = "CTkRadioButton"
    is_container = False
    icon = "radiobutton"
    impl = customtkinter.CTkRadioButton
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)


class CTkScrollBar(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkScrollbar):
    _keys = (
        *_common_keys,
        "border_spacing",
        "button_color",
        "button_hover_color",
        # "minimum_pixel_length",
        # "orientation",
        "hover",
    )

    klass = customtkinter.CTkScrollbar

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


class CTkScrollBarMeta(CTkScrollBar, metaclass=WidgetMeta):
    display_name = "CTkScrollBar"
    is_container = False
    icon = "scrollbar"
    impl = customtkinter.CTkScrollbar
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)


class CTkSegmentedButton(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkSegmentedButton):
    _keys = (
        *_common_keys,
        "border_width",
        "selected_color",
        "selected_hover_color",
        "unselected_color",
        "unselected_hover_color",
        "text_color",
        "text_color_disabled",
        "font",
        "values",
        "variable",
        "state",
        "command",
        "dynamic_resizing",
    )

    klass = customtkinter.CTkSegmentedButton

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)

    def bind(self, sequence=None, func=None, add=None):
        tkinter.Misc.bind(self, sequence, func, add)

    def unbind(self, sequence=None, funcid=None):
        return tkinter.Misc.unbind(self, sequence, funcid)


class CTkSegmentedButtonMeta(CTkSegmentedButton, metaclass=WidgetMeta):
    display_name = "CTkSegmentedButton"
    is_container = False
    icon = "button"
    impl = customtkinter.CTkSegmentedButton
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)
    allow_direct_move = False


class CTkSlider(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkSlider):
    _keys = (
        *_common_keys,
        "border_width",
        "progress_color",
        "border_color",
        "button_color",
        "button_hover_color",
        "orientation",
        "state",
        "hover",
        "command",
        "variable",
        "from_",
        "to",
        "number_of_steps",
    )

    klass = customtkinter.CTkSlider

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


class CTkSliderMeta(CTkSlider, metaclass=WidgetMeta):
    display_name = "CTkSlider"
    is_container = False
    icon = "scale"
    impl = customtkinter.CTkSlider
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)
    allow_direct_move = False


class CTkSwitch(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkSwitch):
    _keys = (
        *_common_keys,
        "border_width",
        "switch_width",
        "switch_height",
        "progress_color",
        "border_color",
        "button_color",
        "button_hover_color",
        # "hover_color",
        "text_color",
        "text",
        "textvariable",
        "font",
        "command",
        "variable",
        # "onvalue",
        # "offvalue",
        "state",
    )

    klass = customtkinter.CTkSwitch

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


class CTkSwitchMeta(CTkSwitch, metaclass=WidgetMeta):
    display_name = "CTkSwitch"
    is_container = False
    icon = "checkbox"
    impl = customtkinter.CTkSwitch
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)


class CTkTextbox(CustomTkMixin, CustomPropertyMixin, customtkinter.CTkTextbox):
    _keys = (
        *_common_keys,
        "border_width",
        "border_spacing",
        "border_color",
        "text_color",
        "scrollbar_button_color",
        "scrollbar_button_hover_color",
        "font",
        # "activate_scrollbars",
        # "state",
        # "wrap",
        # "autoseparators",
        # "cursor",
        # "exportselection",
        # "insertborderwidth",
        # "insertofftime",
        # "insertontime",
        # "insertwidth",
        # "maxundo",
        # "padx",
        # "pady",
        # "selectborderwidth",
        # "spacing1",
        # "spacing2",
        # "spacing3",
        # "tabs",
        # "takefocus",
        # "undo",
        # "xscrollcommand",
        # "yscrollcommand",
    )

    klass = customtkinter.CTkTextbox

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


class CTkTextMeta(CTkTextbox, metaclass=WidgetMeta):
    display_name = "CTkTextbox"
    is_container = False
    icon = "text"
    impl = customtkinter.CTkTextbox
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)
    allow_direct_move = False


class CTkScrollableFrame(CustomTkMixin, BindBypassMixin, CustomPropertyMixin, customtkinter.CTkScrollableFrame):
    _keys = (
        *_common_keys,
        "border_width",
        "border_color",
        "scrollbar_fg_color",
        "scrollbar_button_color",
        "scrollbar_button_hover_color",
        "label_fg_color",
        "label_text_color",
        "label_text",
        "label_font",
        "label_anchor",
        "orientation",
    )

    klass = customtkinter.CTkScrollableFrame

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


# TODO: work around funky custom tkinter scrollable frame

# class CTkScrollableFrameMeta(CTkScrollableFrame, metaclass=WidgetMeta):
#     display_name = "CTkScrollableFrame"
#     # TODO: implement custom scrollable frame layout
#     is_container = False
#     allow_direct_move = False
#     icon = "frame"
#     impl = customtkinter.CTkScrollableFrame
#     DEF_OVERRIDES = with_name(CTK_PROPERTIES)


class CTkTabview(CustomTkMixin, BindBypassMixin, CustomPropertyMixin, customtkinter.CTkTabview):
    _keys = (
        *_common_keys,
        "border_width",
        "border_color",
        "segmented_button_fg_color",
        "segmented_button_selected_color",
        "segmented_button_selected_hover_color",
        "segmented_button_unselected_color",
        "segmented_button_unselected_hover_color",
        "text_color",
        "text_color_disabled",
        "command",
        "anchor",
        "state",
    )

    klass = customtkinter.CTkTabview

    def __init__(self, master=None, **kw):
        self.patch_setter_getter()
        super().__init__(master, **kw)


# TODO Some properties throw errors when tabview has no children

# class CTkTabviewMeta(CTkTabview, metaclass=WidgetMeta):
#     display_name = "CTkTabview"
#     # TODO: implement custom tabview layout
#     is_container = False
#     allow_direct_move = False
#     icon = "tabs"
#     impl = customtkinter.CTkTabview
#     DEF_OVERRIDES = with_name(CTK_PROPERTIES)


class _CTkToplevel(_Toplevel):

    def __init__(self, master):
        # id will be set later
        super().__init__(master, '')


class CTkToplevelEmbed(CustomPropertyMixin, customtkinter.CTkToplevel):
    """Once again, Work-arounds for broken custom tkinter API"""
    _keys = (
        "fg_color",
    )

    def _ext_set_fg_color(self, val):
        customtkinter.CTkToplevel.configure(self, fg_color=val)

    def _ext_fg_color(self):
        return customtkinter.CTkToplevel.cget(self, 'fg_color')

    def maxsize(self, width=None, height=None):
        if width is None and height is None:
            return super(customtkinter.CTkToplevel, self).maxsize(width, height)
        super().maxsize(width, height)

    def minsize(self, width=None, height=None):
        if width is None and height is None:
            return super(customtkinter.CTkToplevel, self).minsize(width, height)
        super().minsize(width, height)

    def wm_iconbitmap(self, bitmap=None, default=None):
        if bitmap is None:
            return super(customtkinter.CTkToplevel, self).wm_iconbitmap(bitmap, default)
        super().wm_iconbitmap(bitmap, default)

    def wm_state(self, newstate=None) -> str:
        if newstate is None:
            return super(customtkinter.CTkToplevel, self).wm_state(newstate)
        if not newstate:
            newstate = "normal"
        try:
            super().wm_state(newstate)
        except tkinter.TclError:
            pass

    state = wm_state


class CTkToplevelMeta(_CTkToplevel, metaclass=WidgetMeta):
    display_name = "CTkTopLevel"
    is_toplevel = True
    is_container = True
    icon = "window"
    impl = customtkinter.CTkToplevel
    embed_class = CTkToplevelEmbed
    embed_frame_class = CTkFrame
    initial_dimensions = 200, 230
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)


class CTkMeta(_CTkToplevel, metaclass=WidgetMeta):
    display_name = "CTk"
    is_toplevel = True
    is_container = True
    icon = "window"
    impl = customtkinter.CTk
    embed_class = CTkToplevelEmbed
    embed_frame_class = CTkFrame
    initial_dimensions = 200, 230
    DEF_OVERRIDES = with_name(CTK_PROPERTIES)


_base_widgets = [
    CTkButton,
    CTkLabel,
    CTkEntry,
    CTkCheckBox,
    CTkComboBox,
    CTkFrame,
    CTkOptionMenu,
    CTkProgressBar,
    CTkRadioButton,
    CTkScrollBar,
    CTkSegmentedButton,
    CTkSlider,
    CTkSwitch,
    CTkTextbox,
    CTkScrollableFrame,
    CTkTabview,
    CTkToplevelEmbed
]

_widgets = [
    CTkButtonMeta,
    CTkLabelMeta,
    CTkEntryMeta,
    CTkCheckBoxMeta,
    CTkComboBoxMeta,
    CTkFrameMeta,
    CTkOptionMenuMeta,
    CTkProgressBarMeta,
    CTkRadioButtonMeta,
    CTkScrollBarMeta,
    CTkSegmentedButtonMeta,
    CTkSliderMeta,
    CTkSwitchMeta,
    CTkTextMeta,
    # CTkScrollableFrameMeta,
    # CTkTabviewMeta,
    CTkToplevelMeta,
    CTkMeta
]


def patch_class_prop_info():
    for klass in _base_widgets:
        klass.prop_info = {
            k: {
                "name": k,
                "default": CTK_PROPERTIES.get(k, {}).get("default"),
                "setter": f"_ext_set_{k}",
                "getter": f"_ext_{k}",
            }
            for k in klass._keys
        }


patch_class_prop_info()


def init(studio):
    component_pane = studio.get_feature(ComponentPane)
    if not component_pane:
        return

    component_pane.register_group(
        "Custom Tkinter",
        _widgets,
        ComponentGroup,
        register=True
    )
