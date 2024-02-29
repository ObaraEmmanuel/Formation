import platform
import sys
import tkinter

from hoverset.ui.widgets import Frame, Label, Application, Hyperlink, Button, ActionNotifier
from hoverset.ui.dialogs import MessageDialog
from hoverset.data.images import load_tk_image
from hoverset.ui.icons import get_icon_image
from hoverset.data.utils import get_resource_path
from hoverset.util import version_description

import formation
import studio


class About(Frame):
    class Spec(Frame):

        def __init__(self, parent, label, value):
            super().__init__(parent, height=20)
            self.config(**self.style.surface)
            Label(self, text=label, **self.style.text, anchor='e').place(x=0, y=0, relwidth=0.5, height=20)
            Label(self, text=value, **self.style.text_passive, anchor='w').place(relx=0.5, y=0, relwidth=0.5, height=20)
            self.pack(side="top", fill="x", padx=10, pady=1)

    def __init__(self, parent):
        super().__init__(parent)
        self.config(**self.style.surface)
        image = load_tk_image(get_resource_path("studio", 'resources/images/logo.png'), 320, 103)
        Label(self, image=image, **self.style.surface).pack(side="top", fill="y", pady=20, padx=50)
        About.Spec(self, "python", sys.version_info)
        About.Spec(self, "tcl/tk", tkinter.TkVersion)
        About.Spec(self, "loader version", version_description(formation.__version__))
        About.Spec(self, "studio version", version_description(studio.__version__))
        About.Spec(self, "Platform", platform.platform())

        copy_button = Button(
            self,
            text="  Copy",
            height=25,
            image=get_icon_image("copy", 14, 14),
            compound="left",
            **self.style.button,
        )
        copy_button.pack(side="top", pady=8)
        copy_button.configure(width=copy_button.measure_text("  Copy") + 25, **self.style.highlight_active)
        ActionNotifier.bind_event("<Button-1>", copy_button, self.copy_to_clipboard, text="Copied")

        f = Frame(self, **self.style.surface)
        f.pack(side="top", padx=10, pady=3)
        Hyperlink(
            f, link="https://formation-studio.readthedocs.io/en/latest/", text="doucumentation"
        ).pack(side='left', anchor='e', padx=3)
        Hyperlink(
            f, link="https://github.com/ObaraEmmanuel/Formation", text="contribute"
        ).pack(side='right', anchor='w', padx=3)
        Hyperlink(
            f, link="https://github.com/ObaraEmmanuel/Formation/issues", text="report issue"
        ).pack(side='right', anchor='w', padx=3)

        Label(self, text="Make designing user interfaces in python a breeze!",
              **self.style.text).pack(side="top", fill="y", pady=5)
        f = Frame(self, **self.style.surface)
        f.pack(side="top")
        Label(f, text="Icons by", **self.style.text_passive).pack(side="left")
        Hyperlink(f, link="https://icons8.com", text="Icons8").pack(side="right")
        copy_right = "Copyright © 2019-2024 Hoverset group"
        Label(self, text=copy_right, **self.style.text_passive).pack(side="top", fill="y")
        self.pack(fill="both", expand=True)

    def copy_to_clipboard(self, _=None):
        self.clipboard_clear()
        self.clipboard_append(
            f"- **Python**: {platform.python_version()} {sys.version_info.releaselevel} {sys.version_info.serial}\n"
            f"- **Tcl/Tk**: {tkinter.TkVersion}\n"
            f"- **Loader**: {formation.__version__}\n"
            f"- **Studio**: {studio.__version__}\n"
            f"- **Platform**: {platform.platform()}"
        )


def about_window(parent):
    dialog = MessageDialog(parent, About)
    dialog.title("Formation")
    dialog.focus_set()
    return dialog


if __name__ == '__main__':
    r = Application()
    About(r).pack(fill="both", expand=True)
    r.mainloop()
