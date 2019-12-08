from hoverset.ui.widgets import Frame, clean_styles, Spinner, Label, SpinBox


class LabelCombo(Frame):

    def __init__(self, master=None, **cnf):
        super().__init__(master)
        default = dict(**self.style.dark, **cnf)
        self.config(clean_styles(self, default))
        self.label = Label(self, **self.style.dark_text, text=" ")
        self.label.pack(side="top", fill="x", pady=2)
        self.dropdown = Spinner(self, **cnf)
        self.dropdown.pack(side="top", pady=2, fill="x")

    def set_label(self, text):
        self.label.config(text=text)

    def set(self, value):
        self.dropdown.set(value)

    def get(self):
        return self.dropdown.get()

    def readonly(self):
        #self.dropdown.set_readonly()
        pass

    def set_values(self, values):
        self.dropdown.set_values(values)


class LabelSpinBox(Frame):

    def __init__(self, master=None):
        super().__init__(master)
        self.config(**self.style.dark)
        self.label = Label(self, **self.style.dark_text, text=" ")
        self.label.pack(side="top", fill="x", pady=2)
        self.entry = SpinBox(self, **self.style.spinbox)
        self.entry.pack(side="top", pady=2, fill="x")

    def set(self, value):
        self.entry.set(value)

    def get(self):
        return self.entry.get()

    def set_label(self, text):
        self.label.config(text=text)

    def align_label(self, direction: str):
        self.label.pack_forget()
        self.entry.pack_forget()
        self.label.pack(side=direction, pady=2, padx=3)
        self.entry.pack(side=direction, pady=2, padx=3)
