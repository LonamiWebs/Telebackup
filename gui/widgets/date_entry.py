from datetime import date, datetime
from tkinter import *
from tkinter.ttk import *


class DateEntry(Frame):
    """Improved entry for inputting dates (day/month/year),
       plus some methods to retrieve the input date or to set it.
    """
    def __init__(self, master=None, **kwargs):
        # Initialize the frame
        super().__init__(master, **kwargs)

        self.day_entry = Entry(self, width=2)
        self.day_entry.bind('<KeyRelease>', self.key_release)
        self.day_entry.grid(row=0, column=0)

        self.separator1 = Label(self, text='/')
        self.separator1.grid(row=0, column=1)

        self.month_entry = Entry(self, width=2)
        self.month_entry.bind('<KeyRelease>', self.key_release)
        self.month_entry.grid(row=0, column=2)

        self.separator2 = Label(self, text='/')
        self.separator2.grid(row=0, column=3)

        self.year_entry = Entry(self, width=4)
        self.year_entry.bind('<KeyRelease>', self.key_release)
        self.year_entry.grid(row=0, column=4)

        self.on_date_changed = None
        self.set_date(datetime.now())

    #region Events

    def key_release(self, event):
        """Fired when the contents change"""
        if self.on_date_changed:
            self.on_date_changed(self.get_date())

    #endregion

    #region Actions

    def set_date(self, value):
        """Sets the given date object in the entry"""
        self.day_entry.delete(0, END)
        self.month_entry.delete(0, END)
        self.year_entry.delete(0, END)

        self.day_entry.insert(0, str(value.day))
        self.month_entry.insert(0, str(value.month))
        self.year_entry.insert(0, str(value.year))

    def get_date(self):
        """Gets the input date object in the entry"""
        try:
            day = int(self.day_entry.get())
            month = int(self.month_entry.get())
            year = int(self.year_entry.get())

            result = date(year=year, month=month, day=day)
            return result

        except ValueError:
            return None

    #endregion
