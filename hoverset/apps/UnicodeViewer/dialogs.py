from tkinter import Toplevel, Label, Frame, ttk, filedialog, TclError
from .widgets import KeyValueLabel, ScrolledGridHolder, Grid, ContextMenu, ActionNotifier
import hoverset.ui.widgets as widgets
from . import components
from PIL import ImageGrab
import win32clipboard
from io import BytesIO
import os


def local_picture_location():
    return os.path.join(os.environ['HOMEDRIVE'], os.environ["HOMEPATH"], "Pictures")


class BaseDialog(widgets.Window):

    def __init__(self, app, **cnf):
        # TODO Figure out how to implement dialog shadow fully
        # self.overlay = Toplevel(app, bg="#5a5a5a")
        # self.overlay.overrideredirect(True)
        # app.update_idletasks()
        # self.overlay.geometry("{}x{}+{}+{}".format(app.winfo_width(), app.winfo_height(),
        #                                            app.winfo_rootx(), app.winfo_rooty()))
        # self.overlay.attributes("-alpha", 0.4)
        # self.overlay.wm_transient(app)
        # self.overlay.tkraise(app)
        # try:
        #     self.overlay.grab_set()
        #     self.overlay.focus_force()
        # except Exception:
        #     pass
        # super().__init__(self.overlay)
        # self.wm_transient(self.overlay)
        super().__init__(app.window, None)
        self.wm_transient(app.window)
        self.config(bg='#5a5a5a')
        self.resizable(0, 0)
        # Icon resource is not accessible during tests so ignore the TclError raised
        try:
            self.iconbitmap("resources/unicode_viewer.ico")
        except TclError:
            pass

        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass
        self.app = app
        self.grid = app.active_grid
        self.body = Frame(self, bg='#f7f7f7')
        self.body.pack(side='top', fill="x", expand=True)
        self.button_holder = Frame(self)
        self.button_holder.pack(side='top', fill='x', expand=True)


class UnicodeInfo(BaseDialog):

    def __init__(self, app):
        super().__init__(app)
        self.data = data = self.grid.data
        Label(self.body, font=(self.grid.font, 28), bg="#5a5a5a", text=self.grid['text'],
              width=5, height=2, fg='#f7f7f7').grid(row=0, column=0, rowspan=len(data), sticky='nesw', padx=5, pady=5)
        # Render the grids data
        row = 1
        for key in data:
            KeyValueLabel(self.body, key, data[key],
                          width=100, height=10).grid(row=row, column=2, sticky='ew')
            row += 1

        close = ttk.Button(self.button_holder, text="Close", command=self.destroy)
        close.pack(side='top', pady=5)

        self.title("Info for {}".format(self.grid.text.replace("0x", "")))


class SaveAsImage(BaseDialog):

    def __init__(self, app):
        super().__init__(app)
        self.image_label = Label(self.body, font=(self.grid.font, 60), fg="#5a5a5a", bg="#f7f7f7",
                                 width=4, height=2, text=self.grid['text'])
        self.image_label.pack(side='top', padx=5, pady=5)

        ActionNotifier.bind_event("<Button-1>",
                                  ttk.Button(self.button_holder, text="copy", command=self.copy_to_clipboard),
                                  self.copy_to_clipboard,
                                  bg="#5a5a5a", fg="#f7f7f7", font="calibri 11", text="Copied to clipboard"
                                  ).pack(side='left', padx=5, pady=5)
        ttk.Button(self.button_holder, text="Save", command=self.save).pack(side='left', padx=5, pady=5)
        ttk.Button(self.button_holder, text="Cancel", command=self.destroy).pack(side='left', padx=5, pady=5)
        self.image = None
        self.title("Save as image")

    def snip_img(self):
        self.update_idletasks()
        self.body.update_idletasks()
        self.image_label.update_idletasks()
        x1 = self.image_label.winfo_rootx()
        y1 = self.image_label.winfo_rooty()
        x2 = self.image_label.winfo_width() + x1
        y2 = self.image_label.winfo_height() + y1
        image = ImageGrab.grab((x1, y1, x2, y2))
        self.image = image

    def save(self):
        if self.image is None:
            self.snip_img()
        shelve = self.app.get_shelve()
        if shelve.get("prev_save_path"):
            start_at = shelve.get("prev_save_path")
            shelve.close()
        else:
            start_at = local_picture_location()
        files = os.listdir(start_at)
        files = list(filter(lambda x: x.startswith("unicode"), files))
        name = f"unicode{len(files)+ 1}"
        name = f"{name}(1).png" if name in files else name + ".png"
        path = filedialog.asksaveasfilename(parent=self, initialfile=name,
                                            filetypes=[("Portable Network Graphics", "*.png")],
                                            initialdir=start_at)
        if path:
            # Ensure that file in pathname has an extension else append default extension png
            shelve = self.app.get_shelve()
            shelve["prev_save_path"] = os.path.dirname(path) # Store path so we can get to it next time
            shelve.close()
            head, file = os.path.split(path)
            file = file if len(file.split(".")) > 1 else file + ".png"
            path = os.path.join(head, file)
            self.image.save(path)
            self.destroy()

    def copy_to_clipboard(self):
        if self.image is None:
            self.snip_img()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, self.convert_img(self.image))
        win32clipboard.CloseClipboard()

    def convert_img(self, image):
        output = BytesIO()
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()
        return data


class ManageFavourites(BaseDialog):

    def __init__(self, app):
        super().__init__(app)
        self.nav = Frame(self.body, bg="#5a5a5a", height=40)
        self.nav.pack(side='top', fill='x', expand=True)
        self.body = ScrolledGridHolder(self.body, height=230, width=400, bg='#f7f7f7')
        self.body.pack(side='top')
        self.body = self.body.body
        self.body.bind('<Leave>', lambda ev: self.deactivate_grid())
        self.grids = []
        self.active_grid = None
        self.load_favourites()
        self.title("Favourites")
        self.context_menu = ContextMenu()
        self.context_menu.load_actions(
            ("\ue923", "Copy unicode", lambda: self.active_grid.copy(0)),
            ("\ue923", "Copy code point", lambda: self.active_grid.copy(2)),
            ("\ue923", "Copy hexadecimal scalar", lambda: self.active_grid.copy(1)),
            ('separator',),
            ("\ue7a9", "Save as image", lambda: SaveAsImage(self)),
            ("\ue8d9", "remove from favorites", self.remove),
            ("\ue946", "unicode info", lambda: UnicodeInfo(self))
        )
        self.components = [
            components.GridTracker(self)
        ]

        ttk.Button(self.button_holder, text="Clear all", command=self.clear_favourites).pack(side='left', padx=5,
                                                                                             pady=5)
        ttk.Button(self.button_holder, text="Close", command=self.destroy).pack(side='right', padx=5, pady=5)

    def request_context_menu(self, event=None):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def activate_grid(self, grid: Grid):
        for component in self.components:
            component.receive_grid(grid)

    def deactivate_grid(self):
        for component in self.components:
            component.receive_grid(self.active_grid)

    def remove(self):
        with self.app.get_favourites() as data:
            fav = data["favourites"]
            fav.remove((self.active_grid.code_point, self.active_grid.font))
            data["favourites"] = fav
        self.active_grid.place_forget()
        self.grids.remove(self.active_grid)
        self.active_grid = None
        self._re_place()

    def clear_favourites(self):
        self.app.set_favourites([])
        for grid in self.grids:
            grid.place_forget()
        self.grids = []

    def get_favourites(self):
        return self.app.favourites_as_list()

    def get_shelve(self):
        return self.app.get_shelve()

    def _re_place(self):
        row, column, max_h = 0, 0, 6
        for grid in self.grids:
            grid.place(x=column * 40, y=row * 40, width=40, height=40)
            if row == max_h - 1:
                column += 1
                row = 0
            else:
                row += 1
        self.body.config(width=(column + 1) * 40, height=max_h * 40)

    def load_favourites(self):
        row, column, max_h = 0, 0, 6
        for grid_config in self.get_favourites():
            grid = Grid(self, font=(grid_config[1], 12))
            grid.set(grid_config[0])
            self.grids.append(grid)
            grid.place(x=column * 40, y=row * 40, width=40, height=40)
            if row == max_h - 1:
                column += 1
                row = 0
            else:
                row += 1
        self.body.config(width=(column + 1) * 40, height=max_h * 40)
