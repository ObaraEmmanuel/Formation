"""
Common dialogs customised for hoverset platform
"""
# ======================================================================= #
# Copyright (C) 2020 Hoverset Group.                                      #
# ======================================================================= #

from hoverset.ui.widgets import Frame, Label, Window, Button, Application, ProgressBar
from hoverset.ui.icons import get_icon_image
from hoverset.platform import platform_is, WINDOWS, MAC


class MessageDialog(Window):
    """
    Main class for creation of hoverset themed alert dialogs. It has the various initialization
    methods for the common dialogs. The supported forms/types are shown below:

    .. _forms:

        * OKAY_CANCEL     :py:meth:`MessageDialog.ask_okay_cancel`
        * YES_NO          :py:meth:`MessageDialog.ask_question`
        * RETRY_CANCEL    :py:meth:`MessageDialog.ask_retry_cancel`
        * SHOW_PROGRESS   :py:meth:`MessageDialog.show_progress`
        * SHOW_WARNING    :py:meth:`MessageDialog.show_warning`
        * SHOW_ERROR      :py:meth:`MessageDialog.show_error`
        * SHOW_INFO       :py:meth:`MessageDialog.show_info`

    There are three icons used in the dialogs:

    .. _icons:

        * :py:attr:`MessageDialog.ICON_ERROR`
        * :py:attr:`MessageDialog.ICON_INFO`
        * :py:attr:`MessageDialog.ICON_WARNING`

    Some dialogs return values while others just notify. Below illustrates using the various dialogs

    .. code-block:: python

        # assuming we have a hoverset Application object app
        # program will wait for value to be obtained

        val = MessageDialog.ask_retry_cancel(
            title="ask_okay",
            message="This is an ask-okay-cancel message",
            parent=app
        )

        # do whatever you need with the value, in this case let's just print the response

        if val == True:
            print("retry")
        elif val == False:
            print("cancel")
        elif val is None:
            print("no value selected")

        # show dialogs don't need to return values
        MessageDialog.show_error(
            title="Error",
            message="This is an error message",
            parent=app
        )

        val = MessageDialog.builder(
            # define the buttons
            {"text": "Continue", "value": "continue", "focus": True},
            {"text": "Pause", "value": "pause"},
            {"text": "Cancel", "value": False},
            wait=True,
            title="Builder",
            message="We just built this dialog from scratch",
            parent=app,
            icon="flame"
        )
        print(val)
        # prints 'continue', 'pause' or False depending on the value of button clicked
    """

    ICON_ERROR = "dialog_error"
    ICON_INFO = "dialog_info"
    ICON_WARNING = "dialog_warning"

    OKAY_CANCEL = "OKAY_CANCEL"
    YES_NO = "YES_NO"
    RETRY_CANCEL = "RETRY_CANCEL"
    SHOW_ERROR = "SHOW_ERROR"
    SHOW_WARNING = "SHOW_WARNING"
    SHOW_INFO = "SHOW_INFO"
    SHOW_PROGRESS = "SHOW_PROGRESS"
    BUILDER = "BUILDER"

    INDETERMINATE = ProgressBar.INDETERMINATE
    DETERMINATE = ProgressBar.DETERMINATE

    _MIN_BUTTON_WIDTH = 60
    _MAX_SHAKES = 10

    def __init__(self, master, render_routine=None, **kw):
        super().__init__(master)
        self.configure(**self.style.surface)
        # ensure the dialog is above the parent window at all times
        self.transient(master)
        # prevent resizing by default
        self.resizable(False, False)
        self.bar = None
        # Common dialogs
        routines = {
            "OKAY_CANCEL": self._ask_okay_cancel,
            "YES_NO": self._ask_yes_no,
            "RETRY_CANCEL": self._ask_retry_cancel,
            "SHOW_ERROR": self._show_error,
            "SHOW_WARNING": self._show_warning,
            "SHOW_INFO": self._show_info,
            "SHOW_PROGRESS": self._show_progress,
            "BUILDER": self._builder  # Allows building custom dialogs
        }
        if render_routine in routines:
            # Completely custom dialogs
            routines[render_routine](**kw)  # noqa
        elif render_routine is not None:
            render_routine(self)
        self.enable_centering()
        self.value = None
        # quirk that prevents explicit window centering on linux for best results
        add = "+" if platform_is(WINDOWS, MAC) else None
        self.bind('<Visibility>', lambda _: self._get_focus(), add=add)
        if platform_is(WINDOWS):
            # This special case fixes a windows specific issue which blocks
            # application from retuning from a withdrawn state
            self.bind('<FocusOut>', lambda _: self.grab_release())
        self.bind('<FocusIn>', lambda _: self._get_focus())
        self._reaction = -1
        self.bind('<Button>', self._on_event)

    def _get_focus(self):
        self.grab_set()

    def _react(self, step):
        """
        Shake the dialog window to gain user attention

        :param step: displacement in pixels, use negative values for
            left displacement and positive for right displacement
        """
        # a value of -1 in self._reaction is a sentinel indicating no reaction is ongoing
        if self._reaction > MessageDialog._MAX_SHAKES:
            self._reaction = -1
            return
        try:
            *_, x, y = self.get_geometry()
            x += step
            self.geometry('+{}+{}'.format(x, y))
            self.after(100, lambda: self._react(step * -1))
            self._reaction += 1
        except Exception:
            self._reaction = -1
            pass

    def _on_event(self, event):
        if not self.event_in(event, self):
            # the user tried to click outside the focused dialog window
            # we'll try to bring their attention back to the dialog
            self.bell()
            if self._reaction < 0:
                # displace by 2 pixels on each shake
                # use larger value for more pronounced displacement
                self._react(2)

    def _make_button_bar(self):
        self.bar = Frame(self, **self.style.surface, **self.style.highlight_dim)
        self.bar.pack(side="bottom", fill="x")

    def _add_button(self, **kw):
        text = kw.get("text")
        focus = kw.get("focus", False)
        # If a button bar does not already exist we need to create one
        if self.bar is None:
            self._make_button_bar()
        btn = Button(self.bar, **self.style.button, text=text, height=25)
        btn.configure(**self.style.highlight_active)
        btn.pack(side="right", padx=5, pady=5)
        # ensure the buttons have a minimum width of _MIN_BUTTON_WIDTH
        btn.configure(width=max(self._MIN_BUTTON_WIDTH, btn.measure_text(text)))
        btn.on_click(kw.get("command", lambda _: self._terminate_with_val(kw.get("value"))))
        if focus:
            btn.focus_set()
            btn.config_all(**self.style.button_highlight)
        return btn

    def _message(self, text, icon=None):
        # set default icon to INFO
        if icon is None:
            icon = self.ICON_INFO
        Label(self, **self.style.text,
              text=text, anchor="w", compound="left", wrap=600, justify="left",
              pady=5, padx=15, image=get_icon_image(icon, 50, 50)
              ).pack(side="top", fill="x")

    def _ask_okay_cancel(self, **kw):
        self.title(kw.get("title", self.title()))
        self._message(kw.get("message"), kw.get("icon", self.ICON_INFO))
        self._add_button(text="Cancel", focus=True, command=lambda _: self._terminate_with_val(False))
        self._add_button(text="Ok", command=lambda _: self._terminate_with_val(True))

    def _ask_yes_no(self, **kw):
        self.title(kw.get("title", self.title()))
        self._message(kw.get("message"), kw.get("icon", self.ICON_INFO))
        self._add_button(text="No", focus=True, command=lambda _: self._terminate_with_val(False))
        self._add_button(text="Yes", command=lambda _: self._terminate_with_val(True))

    def _ask_retry_cancel(self, **kw):
        self.title(kw.get("title", self.title()))
        self._message(kw.get("message"), kw.get("icon", self.ICON_WARNING))
        self._add_button(text="Cancel", command=lambda _: self._terminate_with_val(False))
        self._add_button(text="Retry", focus=True, command=lambda _: self._terminate_with_val(True))

    def _show_error(self, **kw):
        self.title(kw.get("title", self.title()))
        self._message(kw.get("message"), kw.get("icon", self.ICON_ERROR))
        self._add_button(text="Ok", focus=True, command=lambda _: self.destroy())

    def _show_warning(self, **kw):
        self.title(kw.get("title", self.title()))
        self._message(kw.get("message"), kw.get("icon", self.ICON_WARNING))
        self._add_button(text="Ok", focus=True, command=lambda _: self.destroy())

    def _show_info(self, **kw):
        self.title(kw.get("title", self.title()))
        self._message(kw.get("message"), kw.get("icon", self.ICON_INFO))
        self._add_button(text="Ok", focus=True, command=lambda _: self.destroy())

    def _show_progress(self, **kw):
        self.title(kw.get("title", self.title()))
        text = kw.get('message', 'progress')
        icon = None
        if kw.get('icon'):
            icon = get_icon_image(kw.get('icon'), 50, 50)
        Label(self, **self.style.text,
              text=text, anchor="w", compound="left", wrap=600, justify="left",
              pady=5, padx=15, image=icon
              ).pack(side="top", fill="x")
        self.progress = ProgressBar(self)
        self.progress.pack(side='top', fill='x', padx=20, pady=20)
        self.progress.mode(kw.get('mode', ProgressBar.DETERMINATE))
        self.progress.color(kw.get('colors', self.style.colors.get('accent', 'white')))
        self.progress.interval(kw.get('interval', ProgressBar.DEFAULT_INTERVAL))

    def _terminate_with_val(self, value):
        self.value = value
        self.destroy()

    def _builder(self, **kw):
        self.title(kw.get("title", self.title()))
        self._message(kw.get("message"), kw.get("icon", self.ICON_WARNING))
        actions = kw.get("actions")
        for action in actions:
            self._add_button(**action)

    @classmethod
    def ask(cls, form, **kw):
        """
        General method for creation common dialogs. You do not have to use this
        method directly since there are specialized methods as shown below.

        .. table::
            :align: center

            ===================================================  ==================================
            instead of                                           use this
            ===================================================  ==================================
            MessageDialog.ask(MessageDialog.OKAY_CANCEL, ...)    MessageDialog.ask_okay_cancel(...)
            MessageDialog.ask(MessageDialog.RETRY_CANCEL, ...)   MessageDialog.ask_retry_cancel(...)
            MessageDialog.ask(MessageDialog.SHOW_INFO, ...)      MessageDialog.show_info(...)
            MessageDialog.ask(MessageDialog.SHOW_ERROR, ...)     MessageDialog.show_error(...)
            MessageDialog.ask(MessageDialog.SHOW_PROGRESS, ...)  MessageDialog.show_progress(...)
            MessageDialog.ask(MessageDialog.SHOW_WARNING, ...)   MessageDialog.show_warning(...)
            MessageDialog.ask(MessageDialog.YES_NO, ...)         MessageDialog.ask_question(...)
            ===================================================  ==================================

        :param form: The type of dialog to be created as defined in forms_ above
        :param kw: The keywords arguments included. These are the common arguments:

            .. _common_args:

                * **parent**: (Required) A hoverset based toplevel widget such as :class:`hoverset.ui.widgets.Application`
                * **title**: Title to be used for the dialog window
                * **message**: Message to be displayed in the alert dialog
                * **icon**: Icon to be displayed in the dialog. Should be one of these icons_.

            .. warning::
                The ``parent`` argument is mandatory and should always be provided. Absence of the parent
                argument will result in missing theme style definitions and cause errors.

        :return: A value or ``None`` depending on the dialog type. See specialized method for mor details
        """
        parent = kw.get("parent")
        dialog = MessageDialog(parent, form, **kw)
        dialog.wait_window()
        return dialog.value

    @classmethod
    def ask_okay_cancel(cls, **kw):
        """
        Show a dialog windows with two buttons: ``okay`` and ``cancel``

        :param kw: Keyword arguments as defined in common_args_.
        :return: Returns ``True`` if "okay" is selected, ``False`` if "cancel" is selected or
            ``None`` if no choice is selected
        """
        return cls.ask(MessageDialog.OKAY_CANCEL, **kw)

    @classmethod
    def ask_question(cls, **kw):
        """
        Show a dialog window with two button: ``yes`` and ``no``

        :param kw: Keyword arguments as defined in common_args_.
        :return: Returns ``True`` if "yes" is selected, ``False`` if "no" is selected or
            ``None`` if no choice is selected
        """
        return cls.ask(MessageDialog.YES_NO, **kw)

    @classmethod
    def ask_retry_cancel(cls, **kw):
        """
        Show a dialog window with two buttons: ``retry`` and ``cancel``

        :param kw: Keyword arguments as defined in common_args_.
        :return: Returns ``True`` if "retry" is selected, ``False`` if "cancel" is selected or
            ``None`` if no choice is selected
        """
        return cls.ask(MessageDialog.RETRY_CANCEL, **kw)

    @classmethod
    def show_error(cls, **kw):
        """
        Show an error message with an error icon.

        :param kw: Keyword arguments as defined in common_args_.
        :return: ``None``
        """
        parent = kw.get("parent")
        cls(parent, MessageDialog.SHOW_ERROR, **kw)

    @classmethod
    def show_warning(cls, **kw):
        """
        Show an warning message with a warning icon.

        :param kw: Keyword arguments as defined in common_args_.
        :return: ``None``
        """
        parent = kw.get("parent")
        cls(parent, MessageDialog.SHOW_WARNING, **kw)

    @classmethod
    def show_info(cls, **kw):
        """
        Show an info message with an info icon.

        :param kw: Keyword arguments as defined in common_args_.
        :return: ``None``
        """
        parent = kw.get("parent")
        cls(parent, MessageDialog.SHOW_INFO, **kw)

    @classmethod
    def show_progress(cls, **kw):
        """

        :param kw: Config options for the progress dialog

            * **parent**: A hoverset based toplevel widget such as :class:`hoverset.ui.widgets.Application`
            * **title**: Title to be used for the dialog window
            * **message**: Message to be displayed in the alert dialog
            * **icon**: Icon to be displayed in the dialog. Should be one of these icons_.
            * **mode**: One of the two modes

                * :py:attr:`MessageDialog.DETERMINATE`
                * :py:attr:`MessageDialog.INDETERMINATE`

            * **color**: Color to be used for the progressbar
            * **interval**: The update interval in :py:attr:`MessageDialog.INDETERMINATE` in milliseconds.
              The smaller the interval the faster the animation.

        :return: The dialog window. The underlying progressbar can then be accessed through
            the property :py:attr:`MessageDialog.progress`. The progressbar is
            a :class:`hoverset.ui.widgets.ProgressBar` object and can be updated as required
        """
        parent = kw.get("parent")
        dialog = cls(parent, MessageDialog.SHOW_PROGRESS, **kw)
        return dialog

    @classmethod
    def builder(cls, *buttons, **kw):
        """
        Create custom dialogs with custom buttons, icons and return values. An example of the use of a
        builder has been provided at the beginning of this page.

        :param buttons: A tuple containing a dictionary defining the custom buttons with the following keys

            * **text**: Text to be displayed in the button
            * **value**: Value returned when button is clicked
            * **focus**: Whether to focus on button when dialog is displayed. Only a single
              button should have ``focus`` set to ``True``

        :param kw: config options for the builder:

            * **parent**: A hoverset based toplevel widget such as :class:`hoverset.ui.widgets.Application`
            * **title**: Title to be used for the dialog window
            * **message**: Message to be displayed in the alert dialog
            * **icon**: Icon to be displayed in the dialog. Should be one of these icons_.
            * **wait**: Set to ``True`` to suspend the program and wait a value to be returned or
              ``False`` to just continue program execution without waiting for a value. Useful when you just need
              to display a message

        :return: A custom value depending on the custom button clicked. If ``wait = False`` no value is returned.
            If no value is selected by the user ``None`` is returned
        """
        parent = kw.get("parent")
        kw["actions"] = buttons
        dialog = cls(parent, MessageDialog.BUILDER, **kw)
        if kw.get("wait", False):
            dialog.wait_window()
            return dialog.value


if __name__ == '__main__':
    app = Application()
    app.load_styles(r"themes\default.css")
    app.geometry('700x600')
    val = MessageDialog.builder(
        {"text": "Continue", "value": "continue", "focus": True},
        {"text": "Pause", "value": "pause"},
        {"text": "Cancel", "value": False},
        wait=True,
        title="Builder",
        message="We just built this dialog from scratch",
        parent=app,
        icon="flame"
    )
    print(val)
    MessageDialog.ask_retry_cancel(title="ask_okay", message="This is an ask-okay-cancel message", parent=app)
    app.mainloop()
