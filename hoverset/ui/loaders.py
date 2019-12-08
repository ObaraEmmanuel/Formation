#  from hoverset.ui.widgets import Canvas
from tkinter import Canvas, Tk


class RoundSpin(Canvas):
    OUTLINE = 2
    PADDING = 2

    def __init__(self, master=None, **cnf):
        super().__init__(master, **cnf, bg="#303030", highlightthickness=0)
        self._arc = None
        self.after(50, self._redraw)
        self._loop = 0
        self._pulse = 0
        self._markers = [0, 180, 360]

    def _redraw(self):
        self.after(50, self._redraw)
        self._loop += 20
        self._loop %= 360
        self.update_idletasks()
        outline = self.OUTLINE + self.PADDING
        width = self.winfo_width() - outline
        if self._arc is None:
            self._arc = self.create_arc(outline, outline, width, width,
                                        start=90, extent=160, width=self.OUTLINE, outline="#3d8aff", style="arc")
        else:
            self.coords(self._arc, outline, outline, width, width)
            if self._markers[1] < self._loop < self._markers[2]:
                self._pulse += ((self._loop % 180) / 180) * 28
            elif self._markers[0] < self._loop < self._markers[1]:
                self._pulse -= ((self._loop % 180) / 180) * 28
            extent = self._pulse + 160
            self.itemconfigure(self._arc, start=self._loop + -1*self._pulse, extent=extent)


if __name__ == '__main__':
    r = Tk()
    r.config(bg="#303030")
    v = RoundSpin(r, width=30, height=30)
    v.pack(padx=30, pady=30)
    r.mainloop()
