from tkinter import *
from tkinter.ttk import *


class CheckBox(Checkbutton):
    """Already-crafted checkbox which already implements
       an is_checked() boolean function plus an on_changed handler.

       As optional arguments, it can take:
         function on_changed()
    """
    def __init__(self, master=None, **kwargs):

        # Set the custom attributes and pop'em out
        self.on_changed = kwargs.pop('on_changed', None)
        self.checked_var = BooleanVar()

        # Initialize the widget
        super().__init__(master, **kwargs)
        self.config(variable=self.checked_var, command=self.on_changed)

    #region Functions

    def is_checked(self):
        return self.checked_var.get()

    #endregion
