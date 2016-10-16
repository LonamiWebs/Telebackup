import tkinter as tk

from telethon.utils import get_display_name

from gui.main import start_app
from gui.windows.backup import BackupWindow
from utils import get_cached_client, sanitize_string


class SelectDialogWindow(tk.Frame):
    def __init__(self, master=None, **args):
        super().__init__(master)

        self.master.title('Select a conversation')

        self.client = get_cached_client()

        self.pack()
        self.create_widgets()

        # Load dialogs async
        self.after(ms=0, func=self.on_load)

    def on_load(self):
        """Event that occurs after the window has loaded"""
        print('Loading dialogs...')
        self.dialogs, self.entities = self.client.get_dialogs(count=50)
        self.update_conversation_list()
        print('Dialogs loaded.')

    def create_widgets(self):
        # Welcome label
        self.welcome = tk.Label(self,
                                text='Please select a conversation:')
        self.welcome.grid(row=0, columnspan=2)

        # Scroll bar for the list
        self.scrollbar = tk.Scrollbar(self)

        # Conversations list
        self.conversation_list = tk.Listbox(self, yscrollcommand=self.scrollbar.set)
        self.conversation_list.bind("<Double-Button-1>", self.on_next)
        self.scrollbar.config(command=self.conversation_list.yview)

        self.conversation_list.grid(row=1, column=0)
        self.scrollbar.grid(row=1, column=1, sticky=tk.NS)

        # Search box
        self.search_box = tk.Entry(self)
        self.search_box.bind('<KeyPress>', self.search)
        self.search_box.grid(row=2, columnspan=2, sticky=tk.EW)

        # Next button
        self.next = tk.Button(self,
                              text='Next',
                              command=self.on_next)
        self.next.grid(row=3, columnspan=2, sticky=tk.EW)

    def on_next(self, event=None):
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
                    start_app(BackupWindow, entity=entity)

    def update_conversation_list(self):
        search = self.search_box.get().lower()
        self.conversation_list.delete(0, tk.END)

        for entity in self.entities:
            display = sanitize_string(get_display_name(entity))
            if search in display.lower():
                self.conversation_list.insert(tk.END, display)

    def search(self, *args):
        self.update_conversation_list()
