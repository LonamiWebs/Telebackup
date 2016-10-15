import tkinter as tk

from gui.res.loader import load_png


class BetterEntry(tk.Frame):
    """Improved entry with support for validation, delete and paste.
       As optional arguments, it can take:
         field max_length = integer
         function on_change(entry_contents)
         function paste_filter(clipboard_contents) returns string
    """
    def __init__(self, master=None, **kwargs):

        # Set the custom attributes and pop'em out
        self.max_length = kwargs.pop('max_length', None)

        self.on_change = kwargs.pop('on_change', None)
        self.paste_filter = kwargs.pop('paste_filter', None)

        # Initialize the frame
        super().__init__(master, **kwargs)

        # Set up our custom widget
        self.entry = tk.Entry(self)
        self.entry.bind('<KeyRelease>', self.change)
        if self.max_length:
            self.entry.config(width=self.max_length)

        self.entry.grid(row=0, column=0)

        # Erase code button
        self.erase = tk.Button(self,
                               image=load_png('backspace'),
                               width='16',
                               height='16',
                               command=self.clear)
        self.erase.grid(row=0, column=1)

        # Paste code button
        self.paste = tk.Button(self,
                               image=load_png('clipboard'),
                               width='16',
                               height='16',
                               command=self.paste)
        self.paste.grid(row=0, column=2)

    def change(self, event=None):
        """Fired when the contents change. Also activates the validation function"""
        if self.max_length:
            if self.entry.index(tk.END) > self.max_length:
                self.entry.delete(self.max_length, tk.END)

        if self.on_change:
            self.on_change()

    def clear(self):
        """Clears the entry contents"""
        self.entry.delete(0, tk.END)
        self.change()

    def paste(self):
        """Pastes the clipboard contents"""
        self.entry.delete(0, tk.END)
        if self.paste_filter:
            self.entry.insert(0, self.paste_filter(self.clipboard_get()))
        else:
            self.entry.insert(0, self.clipboard_get())

        self.change()

    def get(self):
        """Gets the contents of the entry"""
        return self.entry.get()

    def set(self, content):
        """Sets the contents of the entry"""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, content)
        self.change()

    def enable(self):
        """Enables the widget"""
        self.entry.config(state=tk.NORMAL)
        self.erase.config(state=tk.NORMAL)
        self.paste.config(state=tk.NORMAL)

    def disable(self):
        """Disables the widget"""
        self.entry.config(state=tk.DISABLED)
        self.erase.config(state=tk.DISABLED)
        self.paste.config(state=tk.DISABLED)
