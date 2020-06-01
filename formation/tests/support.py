from formation.loader import ttk, tk

tk_supported = {
    tk.Button, tk.Checkbutton, tk.Label, tk.Menubutton, tk.Scrollbar,
    tk.Canvas, tk.Frame, tk.LabelFrame, tk.Listbox, tk.PanedWindow,
    tk.Entry, tk.Message, tk.Radiobutton, tk.Scale, tk.Spinbox, tk.Text
}

ttk_supported = {
    ttk.Button, ttk.Checkbutton, ttk.Label, ttk.Menubutton, ttk.Progressbar, ttk.Scrollbar, ttk.Separator,
    ttk.Combobox, ttk.Entry, ttk.LabeledScale, ttk.Radiobutton, ttk.Scale, ttk.Spinbox,
    ttk.Frame, ttk.Panedwindow, ttk.Labelframe, ttk.Notebook, ttk.Sizegrip, ttk.Treeview
}
