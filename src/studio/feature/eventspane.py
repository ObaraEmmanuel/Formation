from hoverset.ui.icons import get_icon_image
from hoverset.ui.widgets import (
    Label, CompoundList, Entry, Frame, Checkbutton, Button
)
from studio.feature._base import BaseFeature
from studio.lib.events import EventBinding, make_event


class BindingsTable(CompoundList):
    class EventItem(CompoundList.BaseItem):

        def __init__(self, master, value: EventBinding, index, isolated=False):
            super().__init__(master, value, index, isolated)
            self.parent_list = master

        @property
        def id(self):
            return self.value.id

        def _on_value_change(self):
            event = EventBinding(
                self.id,
                self.sequence.get(),
                self.handler.get(),
                self.add_arg.get(),
            )
            self.parent_list._item_changed(event)

        def _delete_entry(self, *_):
            self.parent_list._item_deleted(self)
            # prevent event propagation since item will be deleted
            return "break"

        def render(self):
            self.config(height=40)
            seq_frame = Frame(self, **self.style.highlight)
            seq_frame.grid(row=0, column=0, sticky="nsew")
            seq_frame.pack_propagate(False)
            self.sequence = Entry(seq_frame, **self.style.input)
            self.sequence.place(x=0, y=0, relwidth=1, relheight=1, width=-40)
            self.sequence.set(self.value.sequence)
            self.sequence.configure(**self.style.no_highlight)
            self.sequence.focus_set()
            self.handler = Entry(self, **self.style.input)
            self.handler.grid(row=0, column=1, sticky="ew")
            self.handler.set(self.value.handler)
            self.handler.config(**self.style.highlight)
            self.add_arg = Checkbutton(self, **self.style.checkbutton)
            self.add_arg.grid(row=0, column=2, sticky="ew")
            self.add_arg.set(self.value.add)
            del_btn = Label(
                self, **self.style.button,
                image=get_icon_image("delete", 14, 14)
            )
            del_btn.grid(row=0, column=3, sticky='nswe')
            del_btn.bind("<Button-1>", self._delete_entry)
            # set the first two columns to expand evenly
            for column in range(2):
                self.grid_columnconfigure(column, weight=1, uniform=1)

            for widget in (self.sequence, self.handler):
                widget.on_change(self._on_value_change)

            self.add_arg._var.trace("w", lambda *_: self._on_value_change())

        def hide(self):
            self.pack_forget()

        def show(self):
            self.pack(fill="x", pady=1, side="top")

        def on_hover(self, *_):
            pass

        def on_hover_ended(self, *_):
            pass

        def update_details(self, value, index):
            self._index = index
            self._value = value
            self.sequence.set(value.sequence)
            self.handler.set(value.handler)
            self.add_arg.set(value.add)

    def __init__(self, master=None, **kwargs):
        super(BindingsTable, self).__init__(master, **kwargs)
        self.set_item_class(BindingsTable.EventItem)
        self._item_pool = []
        self._on_value_change = None
        self._on_delete = None

    def clear(self):
        for item in self.items:
            item.pack_forget()
            self._item_pool.append(item)
        self._items.clear()

    def add(self, *events):
        self.add_values(events)

    def _render(self, values):
        for i, value in enumerate(values):
            if len(self._item_pool):
                item = self._item_pool[0]
                self._item_pool.remove(item)
                item.update_details(value, i)
            else:
                item = self._cls(self, value, i)
            self._items.append(item)
            item.show()
            item.update_idletasks()

    def _remove_item(self, item):
        item.pack_forget()
        self._item_pool.append(item)
        # if item is selected deselect it
        if self.get() == item:
            item.deselect()
            self._current_indices = []

        self._items.remove(item)

    def remove(self, _id):
        for item in filter(lambda i: i.id == _id, self.items):
            self._remove_item(item)
        self._values = tuple(filter(lambda e: e.id != _id, self._values))

    def on_value_change(self, callback, *args, **kwargs):
        self._on_value_change = lambda value: callback(value, *args, **kwargs)

    def on_item_delete(self, callback, *args, **kwargs):
        self._on_delete = lambda value: callback(value, *args, **kwargs)

    def _item_changed(self, value):
        if self._on_value_change:
            self._on_value_change(value)

    def _item_deleted(self, item):
        if self._on_delete:
            self._on_delete(item)

    def hide_all(self):
        for item in self.items:
            item.hide()


class EventPane(BaseFeature):
    name = "Event pane"
    icon = "blank"
    _defaults = {
        **BaseFeature._defaults,
        "side": "right",
    }
    NO_SELECTION_MSG = "You have not selected any widget selected"
    NO_EVENT_MSG = "You have not added any bindings"
    NO_MATCH_MSG = "No items match your search"

    def __init__(self, master, studio, **cnf):
        super().__init__(master, studio, **cnf)
        self.header = Frame(self, **self.style.surface)
        self.header.pack(side="top", fill="x")
        for i, title in enumerate(("Sequence", "Handler", "Add", " " * 3)):
            Label(
                self.header, **self.style.text_passive, text=title,
                anchor="w",
            ).grid(row=0, column=i, sticky='ew')

        # set the first two columns to expand evenly
        for column in range(2):
            self.header.grid_columnconfigure(column, weight=1, uniform=1)

        self.bindings = BindingsTable(self)
        self.bindings.on_value_change(self.modify_item)
        self.bindings.on_item_delete(self.delete_item)
        self.bindings.pack(fill="both", expand=True)

        self._add = Button(
            self._header, **self.style.button, width=25, height=25,
            image=get_icon_image("add", 15, 15)
        )
        self._add.pack(side="right")
        self._add.tooltip("Add event binding")
        self._add.on_click(self.add_new)

        self._search_btn = Button(
            self._header, **self.style.button,
            image=get_icon_image("search", 15, 15), width=25, height=25,
        )
        self._search_btn.pack(side="right")
        self._search_btn.on_click(self.start_search)

        self._empty_frame = Label(self.bindings, **self.style.text_passive)
        self._show_empty(self.NO_SELECTION_MSG)

    def _show_empty(self, message):
        self._empty_frame.place(x=0, y=0, relwidth=1, relheight=1)
        self._empty_frame["text"] = message

    def _remove_empty(self):
        self._empty_frame.place_forget()

    def add_new(self, *_):
        if self.studio.selected is None:
            return
        self._remove_empty()
        new_binding = make_event("<>", "", False)
        widget = self.studio.selected
        if not hasattr(widget, "_event_map_"):
            setattr(widget, "_event_map_", {})
        widget._event_map_[new_binding.id] = new_binding
        self.bindings.add(new_binding)

    def delete_item(self, item):
        widget = self.studio.selected
        if widget is None:
            return
        widget._event_map_.pop(item.id)
        self.bindings.remove(item.id)

    def modify_item(self, value: EventBinding):
        widget = self.studio.selected
        widget._event_map_[value.id] = value

    def on_select(self, widget):
        if widget is None:
            self._show_empty(self.NO_SELECTION_MSG)
            return
        self._remove_empty()
        bindings = getattr(widget, "_event_map_", {})
        values = bindings.values()
        self.bindings.clear()
        self.bindings.add(*values)
        if not len(values):
            self._show_empty(self.NO_EVENT_MSG)

    def start_search(self, *_):
        if self.studio.selected:
            super().start_search()

    def on_search_query(self, query: str):
        showing = 0
        self._remove_empty()
        self.bindings.hide_all()
        for item in self.bindings.items:
            if query in item.value.sequence or query in item.value.handler:
                item.show()
                showing += 1
        if not showing:
            self._show_empty(self.NO_MATCH_MSG)

    def on_search_clear(self):
        self._remove_empty()
        self.bindings.hide_all()
        for item in self.bindings.items:
            item.show()
        super().on_search_clear()
