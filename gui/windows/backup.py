import tkinter as tk
from threading import Thread
from tkinter import ttk

from os.path import isfile
from telethon.utils import get_display_name, get_input_peer

from backuper import Backuper
from gui.res.loader import load_png
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

        self.pack(padx=16, pady=16)
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
        self.title.grid(row=0, columnspan=2, padx=16, pady=(0, 16))


        # Left column
        self.left_column = tk.Frame(self, padx=16)
        self.left_column.grid(row=1, column=0, sticky=tk.NE)

        # Resume/pause backup download
        self.resume_pause = tk.Button(self.left_column,
                                      text='Resume',
                                      image=load_png('resume'),
                                      compound=tk.LEFT)
        self.resume_pause.grid(row=0, sticky=tk.NE)

        # Save (download) media
        self.save_media = tk.Button(self.left_column,
                                    text='Save media',
                                    image=load_png('download'),
                                    compound=tk.LEFT)
        self.save_media.grid(row=1, sticky=tk.N)

        # Export backup
        self.export = tk.Button(self.left_column,
                                text='Export',
                                image=load_png('export'),
                                compound=tk.LEFT)
        self.export.grid(row=2, sticky=tk.NE)

        # Delete saved backup
        self.export = tk.Button(self.left_column,
                                text='Delete',
                                image=load_png('delete'),
                                compound=tk.LEFT)
        self.export.grid(row=3, sticky=tk.NE)

        self.margin = tk.Label(self.left_column, height=1)
        self.margin.grid(row=4, sticky=tk.NE)

        # Go back
        self.back = tk.Button(self.left_column,
                              text='Back',
                              image=load_png('back'),
                              compound=tk.LEFT)
        self.back.grid(row=5, sticky=tk.NE)


        # Right column
        self.right_column = tk.Frame(self)
        self.right_column.grid(row=1, column=1, sticky=tk.NSEW)

        # Let this column (0) expand and contract with the window
        self.right_column.columnconfigure(0, weight=1)

        # Entity card showing stats
        self.entity_card = EntityCard(self.right_column,
                                      entity=self.entity,
                                      padx=16, pady=16)
        self.entity_card.grid(row=0, sticky=tk.EW)

        # Right bottom column
        self.bottom_column = tk.Frame(self.right_column)
        self.bottom_column.grid(row=1, sticky=tk.EW, pady=(16, 0))

        # Let this column (0) also expand and contract with the window
        self.bottom_column.columnconfigure(0, weight=1)

        # Estimated time left
        self.etl = tk.Label(self.bottom_column,
                            text='Estimated time left: ???')
        self.etl.grid(row=0, sticky=tk.W)

        # Download progress bar
        self.progress = ttk.Progressbar(self.bottom_column)
        self.progress.grid(row=1, sticky=tk.EW)

        # Downloaded messages/total messages
        self.text_progress = tk.Label(self.bottom_column,
                                      text='0/??? messages saved')
        self.text_progress.grid(row=2, sticky=tk.E)
