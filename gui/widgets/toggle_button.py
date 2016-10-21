from tkinter import *
from tkinter.ttk import *


class ToggleButton(Button):
    """A toggle button which works like a checkbox,
      and can be checked and unchecked with different text and images"""
    def __init__(self, master=None, **kwargs):
        """Extra parameters:
           checked_text          (str)
           checked_image         (PhotoImage)
           on_toggle(is_checked) (function)

           (text and image both default to the unchecked state)"""

        # Set the custom attributes and pop'em out
        self.unchecked_text = kwargs.get('text')
        self.unchecked_image = kwargs.get('image')

        self.checked_text = kwargs.pop('checked_text', None)
        self.checked_image = kwargs.pop('checked_image', None)

        self.on_toggle = kwargs.pop('on_toggle', None)
        self.is_checked = False

        kwargs['command'] = self.toggle
        kwargs['compound'] = kwargs.get('compound', LEFT)  # Default compound
        super().__init__(master, **kwargs)

    def toggle(self, checked=None):
        """Toggles the button state"""
        if checked is not None:
            self.is_checked = checked
        else:
            self.is_checked = not self.is_checked

        if self.is_checked:
            self.config(text=self.checked_text, image=self.checked_image)
        else:
            self.config(text=self.unchecked_text, image=self.unchecked_image)

        if self.on_toggle:
            self.on_toggle()
