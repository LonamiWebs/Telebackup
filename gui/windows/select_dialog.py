from tkinter import *
from tkinter.ttk import *

from telethon.utils import get_display_name

from backuper import Backuper
from gui import start_app
from utils import get_cached_client, sanitize_string


class SelectDialogWindow(Frame):
    def __init__(self, master=None, **args):
        super().__init__(master)

        # Get a cached client to load the dialogs later
        self.client = get_cached_client()

        # Set up the frame itself
        self.master.title('Select a conversation')
        self.pack()
        self.create_widgets()

        # Load previous backups entities
        self.entities = list(Backuper.enumerate_backups_entities())
        self.update_conversation_list()

        # Load dialogs after the window has loaded (arbitrary 100ms)
        self.after(ms=100, func=self.on_load)

    #region Widgets setup

    def create_widgets(self):
        #                                                           Welcome label
        self.welcome = Label(self,
                             text='Please select a conversation:')
        self.welcome.grid(row=0, columnspan=2)

        #                                                           Scroll bar for the list
        self.scrollbar = Scrollbar(self)

        #                                                           Conversations list
        self.conversation_list = Listbox(self,
                                         yscrollcommand=self.scrollbar.set)
        self.conversation_list.bind("<Double-Button-1>", self.on_next)
        self.scrollbar.config(command=self.conversation_list.yview)

        self.conversation_list.grid(row=1, column=0)
        self.scrollbar.grid(row=1, column=1, sticky=NS)

        #                                                           Search box
        self.search_box = Entry(self)
        self.search_box.bind('<KeyPress>', self.search)
        self.search_box.grid(row=2, columnspan=2, sticky=EW)

        #                                                           Next button
        self.next = Button(self,
                           text='Next',
                           command=self.on_next)
        self.next.grid(row=3, columnspan=2, sticky=EW)

    def update_conversation_list(self):
        """Updates the conversation list with the currently
           loaded entities and filtered by the current search"""
        search = self.search_box.get().lower()
        self.conversation_list.delete(0, END)

        for entity in self.entities:
            display = sanitize_string(get_display_name(entity))
            if search in display.lower():
                self.conversation_list.insert(END, display)

    #endregion

    #region Events

    def on_load(self):
        """Event that occurs after the window has loaded"""
        print('Loading dialogs...')

        # Do not add an entity twice
        for entity in self.client.get_dialogs(count=50)[1]:
            if not any(e for e in self.entities if e.id == entity.id):
                self.entities.append(entity)

        self.update_conversation_list()
        print('Dialogs loaded.')

    #endregion

    #region Button and search actions

    def on_next(self, event=None):
        """Gets fired after the Next button is clicked"""
        # Ensure the user has selected an entity
        selection = self.conversation_list.curselection()
        if selection:
            index = selection[0]
            value = self.conversation_list.get(index)

            # Search for the matching entity (user or chat)
            # TODO Note that this will NOT work if they have the exact same name!
            for entity in self.entities:
                display = sanitize_string(get_display_name(entity))
                if value == display:
                    self.master.destroy()
                    # Import the window here to avoid cyclic dependencies
                    from gui.windows import BackupWindow
                    start_app(BackupWindow, entity=entity)

    def search(self, *args):
        """Gets fired when the search term changes"""
        self.update_conversation_list()

    #endregion
