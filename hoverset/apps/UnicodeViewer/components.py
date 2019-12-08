from tkinter import Frame, Label, ttk, font, StringVar
from .widgets import NavControl, HexadecimalIntegerControl, Grid
from . import dialogs


class Component:

    def __init__(self, app):
        self.nav = Frame(app.nav, bg="#5a5a5a")
        self.app = app
        self.range = [0, 200]

    def render(self):
        self.nav.pack(side="left")

    def receive_range(self):
        self.range = self.app.current_range

    def receive_grid(self, grid):
        pass

    def size_changed(self):
        pass

    def uninstall(self):
        self.nav.pack_forget()
        self.app.components.remove(self)


class RenderRangeControl(Component):

    def __init__(self, app):
        super().__init__(app)
        Label(self.nav, font='calibri 12', text='Code point', bg='#5a5a5a', fg='#f7f7f7').pack(side="left", padx=4)
        self.input = HexadecimalIntegerControl(self.nav, font='calibri 12', width=6, fg="#5a5a5a", bg="#f7f7f7",
                                               bd=1, relief='flat')
        self.input.pack(side="left", padx=3)
        self.input.bind('<Return>', lambda _: self.render_range())
        self.draw = NavControl(self.nav, text=u'\ue895')
        self.draw.pack(side="left")
        self.draw.run = self.render_range
        self.render()

    def render_range(self):
        self.app.render(self.input.get())

    def receive_range(self):
        super().receive_range()
        self.input.set(str(self.range[0]))


class GridTracker(Component):

    def __init__(self, app):
        super().__init__(app)
        self.info = Label(self.app.nav, bg="#5a5a5a", font="calibri 12", fg="#f7f7f7", width=9)
        self.info.pack(side='right')
        self.render()
        self.text = ""

    def render(self):
        self.nav.pack(side="right")

    def receive_grid(self, grid: Grid):
        if grid is None:
            self.info["text"] = self.text = ""
            return
        self.text = grid.text
        self.info["text"] = "{} : {}".format(chr(int(grid.text, 16)), grid.text.replace("0x", ""))


class RenderSizeControl(Component):

    def __init__(self, app):
        super().__init__(app)
        self.nav['bg'] = "#5a5a5a"
        Label(self.nav, font='calibri 12', text='Width', bg='#5a5a5a', fg='#f7f7f7', width=7).grid(row=0, column=0)
        Label(self.nav, font='calibri 12', text='Height', bg='#5a5a5a', fg='#f7f7f7', width=7).grid(row=1, column=0)
        self.width = ttk.Scale(self.nav, from_=6, to=20, length=100, orient='horizontal', command=self.change_width)
        self.width.grid(row=0, column=1)
        self.height = ttk.Scale(self.nav, from_=6, to=10, length=100, orient='horizontal', command=self.change_height)
        self.height.grid(row=1, column=1)
        self.width_val = Label(self.nav, font='calibri 12', bg='#5a5a5a', fg='#f7f7f7', width=2)
        self.width_val.grid(row=0, column=2)
        self.height_val = Label(self.nav, font='calibri 12', bg='#5a5a5a', fg='#f7f7f7', width=2)
        self.height_val.grid(row=1, column=2)
        self.render()

    def size_changed(self):
        self.width.set(self.app.size[0])
        self.height.set(self.app.size[1])

    def change_width(self, _):
        self.app.size = (int(self.width.get()), self.app.size[1])
        self.width_val["text"] = str(self.app.size[0])

    def change_height(self, _):
        self.app.size = (self.app.size[0], int(self.height.get()))
        self.height_val["text"] = str(self.app.size[1])


class Swipe(Component):

    def __init__(self, app):
        super().__init__(app)
        self.prev = NavControl(self.nav, text=u'\ue830')
        self.prev.pack(side="left")
        self.next = NavControl(self.nav, text=u'\uea47')
        self.next.pack(side="left")
        self.next.run = self.next_render
        self.prev.run = self.prev_render
        self.render()

    def next_render(self):
        self.app.render(self.app.current_range[-1])

    def prev_render(self):
        spread = self.app.current_range
        self.app.render(spread[0] - (spread[1] - spread[0]))


class FontSelector(Component):

    def __init__(self, app):
        super().__init__(app)
        self.var = StringVar()
        self.var.trace('w', self.value_changed)
        Label(self.nav, font='calibri 11', text='font family', bg='#5a5a5a', fg='#f7f7f7', width=12).pack(side='top')
        self.input = ttk.Combobox(self.nav, values=self._get_fonts(), style='kim.TCombobox',
                                  width=15, textvariable=self.var)
        self.input.pack(side='top')
        self.input.set('Arial')
        self.render()

    def value_changed(self, *_):
        for column in self.app.grids:
            for grid in column:
                grid['font'] = (self.input.get(), 12)

    def _get_fonts(self):
        fonts = sorted(list(font.families()))
        fonts = list(filter(lambda x: not x.startswith("@"), fonts))
        return fonts


class FavouritesManager(Component):

    def __init__(self, app):
        super().__init__(app)
        fav = NavControl(self.nav, text="\ue735")
        fav.pack(side='right', padx=3)
        fav.run = lambda: dialogs.ManageFavourites(app)
        self.render()
