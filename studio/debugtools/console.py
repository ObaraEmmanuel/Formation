# ======================================================================= #
# Copyright (C) 2024 Hoverset Group.                                      #
# ======================================================================= #

# inspired by https://gist.github.com/olisolomons/e90d53191d162d48ac534bf7c02a50cd

import hashlib
import queue
import tkinter as tk
import traceback

from hoverset.ui.icons import get_icon_image
from hoverset.ui.widgets import Text, AutoScroll, Button
from studio.debugtools.defs import Message
from studio.i18n import _
from studio.ui.widgets import Pane


class Pipe:
    """mock stdin stdout or stderr"""

    def __init__(self):
        self.buffer = queue.Queue()
        self.reading = False

    def write(self, data):
        self.buffer.put(data)

    def flush(self):
        pass

    def clear(self):
        self.buffer.queue.clear()

    def readline(self):
        self.reading = True
        line = self.buffer.get()
        self.reading = False
        return line


class ConsoleText(Text):
    """
    A Text widget which handles some application logic,
    e.g. having a line of input at the end with everything else being uneditable
    """
    PROMPT = ">>> "

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # make edits that occur during on_text_change not cause it to trigger again
        def on_modified(_):
            flag = self.edit_modified()
            if flag:
                self.after(10, self.on_text_change(_))
            self.edit_modified(False)

        self.bind("<<Modified>>", on_modified)

        # store info about what parts of the text have what colour
        # used when colour info is lost and needs to be re-applied
        self.console_tags = []

        # the position just before the prompt (>>>)
        # used when inserting command output and errors
        self.mark_set("prompt_end", 1.0)

        # keep track of where user input/commands start and the committed text ends
        self.committed_hash = None
        self.committed_text_backup = ""
        self.commit_all()

    def clear(self):
        super().clear()
        self.committed_hash = None
        self.committed_text_backup = ""
        self.mark_unset("all")
        self.mark_set("prompt_end", 1.0)
        self.console_tags = []

    def prompt(self):
        """Insert a prompt"""
        self.mark_set("prompt_end", 'end-1c')
        self.mark_gravity("prompt_end", tk.LEFT)
        self.write(self.PROMPT, "prompt", foreground=self.style.colors["secondary1"])
        self.mark_gravity("prompt_end", tk.RIGHT)

    def commit_all(self):
        """Mark all text as committed"""
        self.commit_to('end-1c')

    def commit_to(self, pos):
        """Mark all text up to a certain position as committed"""
        if self.index(pos) in (self.index("end-1c"), self.index("end")):
            # don't let text become un-committed
            self.mark_set("committed_text", "end-1c")
            self.mark_gravity("committed_text", tk.LEFT)
        else:
            # if text is added before the last prompt (">>> "), update the stored position of the tag
            for i, (tag_name, _, _) in reversed(list(enumerate(self.console_tags))):
                if tag_name == "prompt":
                    tag_ranges = self.tag_ranges("prompt")
                    self.console_tags[i] = ("prompt", tag_ranges[-2], tag_ranges[-1])
                    break

        # update the hash and backup
        self.committed_hash = self.get_committed_text_hash()
        self.committed_text_backup = self.get_committed_text()

    def get_committed_text_hash(self):
        """Get the hash of the committed area - used for detecting an attempt to edit it"""
        return hashlib.md5(self.get_committed_text().encode()).digest()

    def get_committed_text(self):
        """Get all text marked as committed"""
        return self.get(1.0, "committed_text")

    def write(self, string, tag_name, pos='end-1c', **kwargs):
        """Write some text to the console"""

        # get position of the start of the text being added
        start = self.index(pos)

        # insert the text
        self.insert(pos, string)
        self.see(tk.END)

        # commit text
        self.commit_to(pos)

        # color text
        self.tag_add(tag_name, start, pos)
        self.tag_config(tag_name, **kwargs)

        # save color in case it needs to be re-colored
        self.console_tags.append((tag_name, start, self.index(pos)))

    def on_text_change(self, _):
        """If the text is changed, check if the change is part of the committed text, and if it is revert the change"""
        if self.get_committed_text_hash() != self.committed_hash:
            # revert change
            self.mark_gravity("committed_text", tk.RIGHT)
            self.replace(1.0, "committed_text", self.committed_text_backup)
            self.mark_gravity("committed_text", tk.LEFT)

            # re-apply colours
            for tag_name, start, end in self.console_tags:
                self.tag_add(tag_name, start, end)

    def read_last_line(self):
        """Read the user input, i.e. everything written after the committed text"""
        return self.get("committed_text", "end-1c")

    def consume_last_line(self):
        """Read the user input as in read_last_line, and mark it is committed"""
        line = self.read_last_line()
        self.commit_all()
        return line


class Console(Pane):
    """A tkinter widget which behaves like an interpreter"""

    def __init__(self, parent, exit_callback, debugger):
        super().__init__(parent)
        self.debugger = debugger

        self.console_frame = AutoScroll(self)
        self.console_frame.pack(fill=tk.BOTH, expand=True)

        self._clear_btn = Button(
            self._header, **self.style.button,
            image=get_icon_image("remove", 20, 20), width=25, height=25,
        )
        self._clear_btn.pack(side="right", padx=2)
        self._clear_btn.tooltip(_("Clear console"))
        self._clear_btn.on_click(lambda *_: self.clear())

        self.text = ConsoleText(self.console_frame, wrap=tk.WORD, font=("Consolas", 12))
        self.text.pack(fill=tk.BOTH, expand=True)
        self.text.bind("<Up>", self._on_up)
        self.text.bind("<Down>", self._on_down)
        self.text.bind("<Left>", self._on_left)
        self.console_frame.set_child(self.text)
        self.console_frame.show_scroll(AutoScroll.Y)

        # make the enter key call the self.enter function
        self.text.bind("<Return>", self.enter)
        self.prompt_flag = True
        self.mark_input_flag = True
        self.command_running = False
        self.stdin_reading = False
        self.history_index = -1
        self.last_typed = ""
        self.exit_callback = exit_callback

        self.stdout = Pipe()
        self.stderr = Pipe()
        self.stdin = Pipe()

        self.pipes = {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "stdin": self.stdin,
        }

        def loop():
            self.read_from_pipe(self.stdout, "stdout")
            self.read_from_pipe(self.stderr, "stderr", foreground='#eb4765')

            self.after(50, loop)

        self.after(50, loop)

    def handle_msg(self, msg):
        if "note" in msg:
            if msg["note"] == "COMMAND_COMPLETE":
                self.command_running = False
            if msg["note"] == "START_STDIN_READ":
                self.stdin_reading = True
            if msg["note"] == "STOP_STDIN_READ":
                self.stdin_reading = False
            return

        tag = msg.get("tag")
        if tag not in self.pipes:
            return
        pipe = self.pipes[tag]
        meth = msg.get("action")
        args = msg.get("args", [])
        getattr(pipe, meth)(*args)

    def clear(self):
        self.text.clear()
        self.stdin.clear()
        self.stdout.clear()
        self.stderr.clear()
        self.prompt()

    def mark_input(self):
        self.mark_input_flag = True

    def _mark_input(self):
        self.text.mark_set("input", "end-1c")
        self.text.mark_gravity("input", tk.LEFT)
        self.mark_input_flag = False

    def is_valid_input_pos(self, index):
        if isinstance(index, str):
            index = self._idx(index)
        inpt = self._idx("input")
        return index >= inpt

    def _idx(self, tag):
        index = self.text.index(tag)
        return tuple(map(int, index.split('.')))

    def _on_up(self, _):
        cur = self._idx(tk.INSERT)
        ins = (cur[0] - 1, cur[1])

        if not self.is_valid_input_pos(ins) and self.is_valid_input_pos(cur):
            if self.command_running:
                return 'break'

            history = self.debugger.pref.get("console::history")
            current = self.text.get("input", "end-1c")

            if self.history_index == -1 or current != history[self.history_index]:
                self.last_typed = current
                self.history_index = -1

            if self.history_index + 1 < len(history):
                self.text.delete("input", tk.END)
                self.history_index += 1
                self.text.insert("input", history[self.history_index])

            return 'break'

    def _on_down(self, _):
        if self._idx(tk.END)[0] - 1 == self._idx(tk.INSERT)[0] and self.is_valid_input_pos(tk.INSERT):
            if self.command_running:
                return 'break'
            history = self.debugger.pref.get("console::history")

            if self.history_index > 0:
                self.history_index -= 1
                self.text.delete("input", tk.END)
                self.text.insert("input", history[self.history_index])
            elif self.history_index == 0:
                self.text.delete("input", tk.END)
                self.text.insert("input", self.last_typed)
                self.history_index -= 1

    def _on_left(self, _):
        ins = self._idx(tk.INSERT)
        ins = (ins[0], ins[1] - 1)

        if not self.is_valid_input_pos(ins):
            return 'break'

    def _on_tap(self, event):
        ins = self._idx(tk.CURRENT)
        if not self.is_valid_input_pos(ins):
            return 'break'

    def prompt(self):
        """Add a '>>> ' to the console"""
        self.prompt_flag = True

    def read_from_pipe(self, pipe: Pipe, tag_name, **kwargs):
        """Method for writing data from the replaced stdout and stderr to the console widget"""

        # write the >>>
        if self.prompt_flag and not self.command_running:
            self.text.prompt()
            self._mark_input()
            self.prompt_flag = False

        # mark the start of the input area
        if self.mark_input_flag:
            self._mark_input()

        # get data from buffer
        string_parts = []
        while not pipe.buffer.empty():
            part = pipe.buffer.get()
            string_parts.append(part)

        # write to console
        str_data = ''.join(string_parts)
        if str_data:
            if self.command_running:
                insert_position = "end-1c"
            else:
                insert_position = "prompt_end"

            self.text.write(str_data, tag_name, insert_position, **kwargs)

    def enter(self, _):
        """The <Return> key press handler"""
        if self.text.index(tk.INSERT) != self.text.index(tk.END):
            self.text.mark_set(tk.INSERT, tk.END)

        if self.stdin_reading:
            # if stdin requested, then put data in stdin instead of running a new command
            line = self.text.consume_last_line()
            line = line + '\n'
            line = line.lstrip('\n')
            self.debugger.transmit(
                Message("CONSOLE", payload={"tag": "stdin", "meth": "_write", "args": [line]}), response=True
            )
            return

        # don't run multiple commands simultaneously
        if self.command_running:
            return 'break'

        # get the command text
        command = self.text.read_last_line()
        try:
            # compile it
            compiled = self.debugger.transmit(Message(
                "HOOK", payload={"meth": "console_compile", "args": (command,)}
            ), response=True)
            if isinstance(compiled, Exception):
                raise compiled
        except (SyntaxError, OverflowError, ValueError):
            # if there is an error compiling the command, print it to the console
            self.text.consume_last_line()
            self.prompt()
            # limit the traceback to avoid exposing the underlying compilation error
            self.debugger.transmit(Message(
                "CONSOLE", payload={"tag": "stderr", "meth": "write", "args": [traceback.format_exc(limit=0)]}
            ), response=True)
            return

        # if it is a complete command
        if compiled:
            # consume the line and run the command
            self.text.consume_last_line()
            self.prompt()
            self.mark_input()
            self.command_running = True
            self.debugger.transmit(Message(
                "HOOK", payload={"meth": "console_run"}
            ), response=True)
            if command:
                self.debugger.pref.update_console_history(command)
            self.history_index = -1
