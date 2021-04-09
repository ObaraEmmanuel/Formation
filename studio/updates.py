import json
import subprocess
import sys
from urllib.request import urlopen
from urllib.error import URLError

from hoverset.ui.dialogs import MessageDialog
from hoverset.ui.widgets import Frame, ProgressBar, Label, Button, Text
from hoverset.ui.icons import get_icon_image
from hoverset.util.execution import as_thread
from hoverset.data.actions import get_routine

import formation


class Updater(Frame):

    def __init__(self, master):
        super().__init__(master)
        self.config(**self.style.surface)
        self._progress = ProgressBar(self)
        self._progress.pack(side="top", fill="x", padx=20, pady=20)
        self._progress_text = Label(
            self, **self.style.text_small,
            anchor="w"
        )
        self._progress_text.pack(side="top", fill="x", padx=20, pady=10)
        self._message = Label(
            self, **self.style.text,
            anchor="w", compound="left", wrap=400, justify="left",
            pady=5, padx=5,
        )
        self._action_btn = Button(
            self, text="Retry", **self.style.button_highlight, width=80, height=25
        )
        self.extra_info = Text(self, width=40, height=6, state='disabled', font='consolas 10')
        self.pack(fill="both", expand=True)
        self.check_for_update()

    def show_button(self, text, func):
        self._action_btn.config(text=text)
        self._action_btn.on_click(func)
        self._action_btn.pack(side="bottom", anchor="e", pady=5, padx=5)

    def show_progress(self, message):
        self.clear_children()
        self._progress_text.configure(text=message)
        self._progress.pack(side="top", fill="x", padx=20, pady=20)
        self._progress_text.pack(side="top", fill="x", padx=20, pady=10)

    def show_error(self, message, retry_func):
        self.show_error_plain(message)
        self.show_button("Retry", retry_func)

    def show_error_plain(self, message):
        self.show_message(message, MessageDialog.ICON_ERROR)

    def update_found(self, version):
        self.show_info(f"New version formation-studio {version} found. Do you want to install?")
        self.show_button("Install", lambda _: self.install(version))

    def show_info(self, message):
        self.show_message(message, MessageDialog.ICON_INFO)

    def show_message(self, message, icon):
        self.clear_children()
        self._message.configure(text=message, image=get_icon_image(icon, 50, 50))
        self._message.pack(side="top", padx=20, pady=10)

    def install(self, version):
        self.show_progress(f"Updating to formation-studio {version}")
        self.upgrade(version)

    @classmethod
    def check(cls, master):
        dialog = MessageDialog(master, cls)
        dialog.title("Formation updater")
        dialog.focus_set()
        return dialog

    @as_thread
    def check_for_update(self, *_):
        self._progress.mode(ProgressBar.INDETERMINATE)
        self.show_progress("Checking for updates ...")
        try:
            content = urlopen("https://pypi.org/pypi/formation-studio/json").read()
            data = json.loads(content)
            ver = data["info"]["version"]
            if ver <= formation.__version__:
                self.show_info("You are using the latest version")
            else:
                self.update_found(ver)
        except URLError:
            self.show_error(
                "Failed to connect. Check your internet connection"
                " and try again.",
                self.check_for_update
            )

    @as_thread
    def upgrade(self, version):
        try:
            # run formation cli upgrade command
            proc_info = subprocess.run(
                [sys.executable, "-m", "studio", "-u"],
                capture_output=True
            )
            if proc_info.returncode != 0 or proc_info.stderr:
                self.show_error_plain(
                    "Something went wrong. Failed to upgrade formation-studio"
                    f" to version {version} ,"
                    f" Exited with code: {proc_info.returncode}"
                )
                if proc_info.stderr:
                    self.extra_info.config(state="normal")
                    self.extra_info.pack(side="top", fill="x", padx=20, pady=10)
                    self.extra_info.clear()
                    self.extra_info.set(str(proc_info.stderr))
                    self.extra_info.config(state="disabled")
            else:
                self.show_info("Upgrade successful. Restart to complete installation")
                self.show_button("Restart", lambda _: get_routine("STUDIO_RESTART").invoke())
                return
        except Exception as e:
            self.show_error_plain(e)

        self.show_button("Retry", lambda _: self.install(version))
