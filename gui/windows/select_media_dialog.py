from tkinter import *
from tkinter.ttk import *

from gui.widgets import CheckBox, DateEntry
from utils import size_to_str


class SelectMediaDialog:
    def __init__(self, parent, size_calculator):
        self.top = Toplevel(parent)

        # Save our required arguments for later use
        self.size_calculator = size_calculator
        self.result = None

        # Set up the frame itself
        self.create_widgets()

    #region Widget setup

    def create_widgets(self):
        # Item selection
        self.select_items = Label(self.top, text='Select the items to download:')
        self.select_items.grid(row=0, sticky=W)

        # [x] Download profile pictures
        self.propics_checkbox = CheckBox(self.top, on_changed=self.refresh_size,
                                         text='Download profile pictures')
        self.propics_checkbox.grid(row=1, sticky=W)

        # [x] Download photos
        self.photos_checkbox = CheckBox(self.top, on_changed=self.refresh_size,
                                        text='Download photos')
        self.photos_checkbox.grid(row=2, sticky=W)

        # [x] Download documents
        self.docs_checkbox = CheckBox(self.top, on_changed=self.refresh_size,
                                      text='Download documents')
        self.docs_checkbox.grid(row=3, sticky=W)

        # Extra filters when downloading the selected items
        self.select_extra = Label(self.top, text='Select extra filters:')
        self.select_extra.grid(row=4, sticky=W)

        # Only documents smaller than a given size (in MB)
        self.only_smaller_frame = Frame(self.top)
        self.only_smaller_frame.grid(row=5, sticky=W)

        self.only_smaller_checkbox = CheckBox(self.only_smaller_frame,
                                              on_changed=self.refresh_size,
                                              text='Only download documents smaller than')
        self.only_smaller_checkbox.grid(row=0, column=0, sticky=W)

        self.only_smaller_entry = Entry(self.only_smaller_frame, width=6)
        self.only_smaller_entry.insert(0, '2')  # 2MB default
        self.only_smaller_entry.grid(row=0, column=1, sticky=W)

        self.only_smaller_units = Label(self.only_smaller_frame, text='MB')
        self.only_smaller_units.grid(row=0, column=2, sticky=W)

         # Do NOT download media before a given date
        self.skip_before_frame = Frame(self.top)
        self.skip_before_frame.grid(row=6, sticky=W)

        self.skip_before_checkbox = CheckBox(self.skip_before_frame,
                                             on_changed=self.refresh_size,
                                             text='Do not download media before:')
        self.skip_before_checkbox.grid(row=0, column=0, sticky=W)

        self.skip_before_date = DateEntry(self.skip_before_frame)
        self.skip_before_date.grid(row=0, column=1, sticky=W)

         # Do NOT download media after a given date
        self.skip_after_frame = Frame(self.top)
        self.skip_after_frame.grid(row=7, sticky=W)

        self.skip_after_checkbox = CheckBox(self.skip_after_frame,
                                            on_changed=self.refresh_size,
                                            text='Do not download media after:')
        self.skip_after_checkbox.grid(row=0, column=0, sticky=W)

        self.skip_after_date = DateEntry(self.skip_after_frame)
        self.skip_after_date.grid(row=0, column=1, sticky=W)

        # Label showing the estimated download size (size_calculator(**result))
        self.estimated_size = Label(self.top)
        self.estimated_size.grid(row=8, sticky=W)

        # Frame showing the cancel and OK buttons
        self.cancel_ok_frame = Frame(self.top)
        self.cancel_ok_frame.grid(row=9, sticky=EW)
        self.top.columnconfigure(0, weight=1)

        self.cancel_button = Button(self.cancel_ok_frame, text='Cancel', command=self.cancel)
        self.cancel_button.grid(row=0, column=0, sticky=W)

        self.ok_button = Button(self.cancel_ok_frame, text='Accept', command=self.accept)
        self.ok_button.grid(row=0, column=1, sticky=E)

    #endregion

    #region Button actions

    def cancel(self):
        """Gets fired after the Cancel button is clicked"""
        self.top.destroy()

    def accept(self):
        """Gets fired after the Accept button is clicked"""
        self.result = self.get_current_result()
        self.top.destroy()

    def get_current_result(self):
        """Returns the current result dictionary,
           based on the selected items and input fields"""

        # Determine whether there's a maximum size
        docs_max_size = None
        if self.only_smaller_checkbox.is_checked():
            try:
                docs_max_size = float(self.only_smaller_entry.get())
                #          MB ->  KB -> bytes
                docs_max_size *= 1024 * 1024
            except ValueError:
                pass

        # Determine whether there are limit dates
        after_date = None
        if self.skip_before_checkbox.is_checked():
            after_date = self.skip_before_date.get_date()

        before_date = None
        if self.skip_after_checkbox.is_checked():
            before_date = self.skip_after_date.get_date()

        # Build the result dictionary
        return {
            'dl_propics': self.propics_checkbox.is_checked(),
            'dl_photos': self.photos_checkbox.is_checked(),
            'dl_docs': self.docs_checkbox.is_checked(),
            'docs_max_size': docs_max_size,
            'after_date': after_date,
            'before_date': before_date
        }

    #endregion

    #region GUI updating and events

    @staticmethod
    def show_dialog(parent, size_calculator=None):
        """Shows the Select Media Dialog.
           A size_calculator must be given (taking this dialogs result as parameter),
           which returns the estimated download size based on the selection"""
        dialog = SelectMediaDialog(parent, size_calculator=size_calculator)
        parent.wait_window(dialog.top)
        return dialog.result

    def refresh_size(self):
        """Refreshes the size (estimated download size) label"""
        size = self.size_calculator(**self.get_current_result())
        self.estimated_size.config(text='Estimated download size: {}'.format(size_to_str(size)))

    #endregion
