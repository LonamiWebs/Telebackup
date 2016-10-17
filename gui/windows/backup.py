import tkinter as tk
from threading import Thread
from tkinter import ttk

from os.path import isfile
from telethon.utils import get_display_name, get_input_peer

from backuper import Backuper
from gui.widgets.entity_card import EntityCard
from utils import get_cached_client, sanitize_string


class BackupWindow(tk.Frame):
    def __init__(self, master=None, **args):
        super().__init__(master)

        self.entity = args['entity']
        self.display = sanitize_string(get_display_name(self.entity))

        self.client = get_cached_client()
        self.backuper = Backuper(self.client, self.entity)

        self.master.title('Backup with {}'.format(self.display))

        self.pack()
        self.create_widgets()

        # Download the profile picture in a different thread
        Thread(target=self.dl_propic).start()

    def dl_propic(self):
        self.entity_card.update_profile_photo(self.backuper.backup_propic())

    def create_widgets(self):
        # Title label
        self.title = tk.Label(self,
                              text='Backup generation for {}'.format(self.display),
                              font='-weight bold -size 18')
        self.title.grid(row=0, columnspan=2, padx=10, pady=10)


        # Left column
        self.left_column = tk.Frame(self)
        self.left_column.grid(row=1, column=0, sticky=tk.NE)

        # Resume/pause backup download
        self.resume_pause = tk.Button(self.left_column,
                                      text='Resume')
        self.resume_pause.grid(row=0, sticky=tk.E)

        # Save (download) media
        self.save_media = tk.Button(self.left_column,
                                    text='Save media')
        self.save_media.grid(row=1, sticky=tk.E)

        # Export backup
        self.export = tk.Button(self.left_column,
                                    text='Export')
        self.export.grid(row=2, sticky=tk.E)

        # Delete saved backup
        self.export = tk.Button(self.left_column,
                                    text='Delete')
        self.export.grid(row=3, sticky=tk.E)

        # Go back
        self.back = tk.Button(self.left_column,
                                    text='Back')
        self.back.grid(row=4, sticky=tk.E)


        # Right column
        self.right_column = tk.Frame(self)
        self.right_column.grid(row=1, column=1)

        # Entity card showing stats
        self.entity_card = EntityCard(self.right_column,
                                      entity=self.entity)
        self.entity_card.grid(row=0)

        # Right bottom column
        self.bottom_column = tk.Frame(self.right_column)
        self.bottom_column.grid(row=1)

        # Estimated time left
        self.etl = tk.Label(self.bottom_column,
                            text='Estimated time left: ???')
        self.etl.grid(row=0)

        # Download progress bar
        self.progress = ttk.Progressbar(self.bottom_column,
                                        length=200)
        self.progress.grid(row=1)

        # Downloaded messages/total messages
        self.text_progress = tk.Label(self.bottom_column,
                                      text='0/??? messages saved')
        self.text_progress.grid(row=2, sticky=tk.E)
