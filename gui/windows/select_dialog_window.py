from tkinter import *
from tkinter.ttk import *

from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from telethon.utils import get_display_name, get_input_peer

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
        self.last_date = None
        self.update_conversation_list()

        # Load dialogs after the window has loaded (arbitrary 100ms)
        self.after(ms=100, func=self.load_more_dialogs)

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

        #                                                           Load more
        self.load_more = Button(self,
                                text='Load more',
                                command=self.load_more_dialogs,
                                state=DISABLED)
        self.load_more.grid(row=3, columnspan=2, sticky=EW)

        #                                                           Next button
        self.next = Button(self,
                           text='Next',
                           command=self.on_next)
        self.next.grid(row=4, columnspan=2, sticky=EW)

    def update_conversation_list(self):
        """Updates the conversation list with the currently
           loaded entities and filtered by the current search"""
        search = self.search_box.get().lower()
        self.conversation_list.delete(0, END)

        for entity in self.entities:
            display = sanitize_string(get_display_name(entity))
            if display and search in display.lower():
                self.conversation_list.insert(END, display)

    #endregion

    #region Events

    def load_more_dialogs(self):
        """Event used to load more dialogs on the button press"""
        print('Loading dialogs...')
        self.load_more.config(state=DISABLED)

        r = self.client.invoke(GetDialogsRequest(offset_date=self.last_date,
                                                 offset_id=0,
                                                 offset_peer=InputPeerEmpty(),
                                                 limit=20))
        for entity in r.users:
            # Do not add an entity twice
            if not any(e for e in self.entities if e.id == entity.id):
                self.entities.append(entity)

        for entity in r.chats:
            if not any(e for e in self.entities if e.id == entity.id):
                self.entities.append(entity)

        if r.messages:
            self.last_date = r.messages[-1].date

        self.update_conversation_list()
        self.load_more.config(state=NORMAL)
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
