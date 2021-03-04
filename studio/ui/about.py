from hoverset.ui.widgets import Frame, Label
from hoverset.ui.dialogs import MessageDialog
from hoverset.data.images import load_tk_image
from hoverset.data.utils import get_resource_path
from hoverset.util import version_description

import formation


class About(Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.config(**self.style.surface)
        image = load_tk_image(get_resource_path('studio', 'resources/images/logo.png'), 400, 129)
        Label(self, image=image, **self.style.surface).pack(side="top", fill="y")
        Label(self,
              text="Version {}".format(
                  version_description(formation.__version__)
              ),
              **self.style.text).pack(side="top", fill="y", pady=15)
        Label(self, text="Make designing user interfaces in python a breeze!",
              **self.style.text).pack(side="top", fill="y", pady=5)
        copy_right = "Copyright © 2019-2021 Hoverset group"
        Label(self, text=copy_right, **self.style.text_passive).pack(side="top", fill="y")
        self.pack(fill="both", expand=True)


def about_window(parent):
    dialog = MessageDialog(parent, About)
    dialog.title("Formation")
    dialog.focus_set()
    return dialog
