from enum import Enum, unique
from hoverset.ui.widgets import Frame
from hoverset.ui.icons import get_icon

#  ===================================== categories =========================================


@unique
class Categories(Enum):
    IMAGE_PROCESSING = ("Image processing", get_icon("image_light"))
    AUDIO_PROCESSING = ("Audio processing", get_icon("equalizer"))
    DEVELOPER_TOOLS = ("Developer", get_icon("developer"))
    MATHEMATICAL_TOOLS = ("Mathematics", get_icon("calculator"))
    NETWORK_TOOLS = ("Network", get_icon("network"))
    SECURITY_TOOLS = ("Security", get_icon("security"))
    GAMES = ("Fun and Games", get_icon("gaming"))
    DATA_MANAGEMENT = ("Data management", get_icon("data"))
    OTHER = ("Miscellaneous", get_icon("play"))

# ===========================================================================================


class BaseApp(Frame):
    icon = get_icon("play")
    CATEGORY = Categories.OTHER
    NAME = "Unknown"

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf)

    def show(self):
        self.pack(fill="both", expand=True)

    def close(self):
        self.pack_forget()

    def open_in(self, parent):
        # To be implemented when the technology actually exists! :(
        pass
