import tkinter as tk

from telethon.utils import get_display_name

from utils import get_cached_client, sanitize_string


class SelectDialogWindow(tk.Frame):
    def __init__(self, master=None, **args):
        super().__init__(master)

        self.master.title('Select a conversation')

        self.client = get_cached_client()

        self.pack()
        self.create_widgets()

        print('Loading dialogs...')
        self.dialogs, self.entities = self.client.get_dialogs(count=50)
        self.update_conversation_list()
        print('Dialogs loaded.')

    def create_widgets(self):
        # Welcome label
        self.welcome = tk.Label(self,
                                text='Please select a conversation:')
        self.welcome.pack()

        # Scroll bar for the list
        self.scrollbar = tk.Scrollbar(self)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Conversations list
        self.conversation_list = tk.Listbox(self, yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.conversation_list.yview)
        self.conversation_list.pack()

        # Search box
        self.search_box = tk.Entry()
        self.search_box.pack()
        self.search_box.bind('<KeyPress>', self.search)

        # Next button
        self.next = tk.Button(self,
                              text='Next')
        self.next.pack(side=tk.BOTTOM, fill=tk.X)

    def update_conversation_list(self):
        search = self.search_box.get().lower()
        self.conversation_list.delete(0, tk.END)

        for entity in self.entities:
            display = sanitize_string(get_display_name(entity))
            if search in display.lower():
                self.conversation_list.insert(tk.END, display)

    def search(self, *args):
        self.update_conversation_list()
