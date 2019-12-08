from hoverset.ui.widgets import ScrolledFrame, Frame


class DesignPad(Frame):

    def __init__(self, master, studio, **cnf):
        super().__init__(master, **cnf)
        self.objects = []
        self.studio = studio