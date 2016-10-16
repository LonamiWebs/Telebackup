import tkinter as tk
from tkinter import ttk

from telethon.utils import get_display_name

from gui.widgets.entity_card import EntityCard
from utils import get_cached_client, sanitize_string


class BackupWindow(tk.Frame):
    def __init__(self, master=None, **args):
        super().__init__(master)

        self.entity = args['entity']
        self.display = sanitize_string(get_display_name(self.entity))

        self.master.title('Backup with {}'.format(self.display))

        self.client = get_cached_client()

        self.pack()
        self.create_widgets()

    def create_widgets(self):
        # Title label
        self.title = tk.Label(self,
                              text='Backup generation for {}'.format(self.display))
        self.title.grid(row=0)

        # Entity card showing stats
        self.entity_card = EntityCard(self,
                                     entity=self.entity)
        self.entity_card.grid(row=1)

        self.progress = ttk.Progressbar(self)
        self.progress.grid(row=2)

        # Downloaded messages/Total messages
        self.text_progress = tk.Label(self)
        self.text_progress.grid(row=3, sticky=tk.E)

        self.etl = tk.Label(self)
        self.etl.grid(row=4)
