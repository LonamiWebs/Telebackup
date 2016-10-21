from tkinter import *
from tkinter.ttk import *

from threading import Thread

from os.path import isfile
from telethon.utils import get_display_name, get_input_peer

from backuper import Backuper
from gui.main import start_app
from gui.res.loader import load_png
from gui.widgets.entity_card import EntityCard
from utils import get_cached_client, sanitize_string


class BackupWindow(Frame):
    def __init__(self, master=None, **args):
        super().__init__(master)

        self.entity = args['entity']
        self.display = sanitize_string(get_display_name(self.entity))

        self.client = get_cached_client()
        self.backuper = Backuper(self.client, self.entity)
        self.backuper.on_metadata_change = self.on_metadata_change

        self.master.title('Backup with {}'.format(self.display))

        self.pack(padx=16, pady=16)
        self.create_widgets()

        # Download the profile picture in a different thread
        Thread(target=self.dl_propic).start()

        # Fire the on_metadata to update some values
        self.on_metadata_change()

    def dl_propic(self):
        self.entity_card.update_profile_photo(self.backuper.backup_propic())

    def create_widgets(self):
        # Title label
        self.title = Label(self,
                           text='Backup generation for {}'.format(self.display),
                           font='-weight bold -size 18',
                           padding=(16, 0, 16, 16))
        self.title.grid(row=0, columnspan=2)


        # Left column
        self.left_column = Frame(self, padding=(16, 0))
        self.left_column.grid(row=1, column=0, sticky=NE)

        # Resume/pause backup download
        self.resume_pause = Button(self.left_column,
                                   text='Resume',
                                   image=load_png('resume'),
                                   compound=LEFT,
                                   command=self.resume_pause_backup)
        self.resume_pause.grid(row=0, sticky=NE)

        # Save (download) media
        self.save_media = Button(self.left_column,
                                 text='Save media',
                                 image=load_png('download'),
                                 compound=LEFT)
        self.save_media.grid(row=1, sticky=N)

        # Export backup
        self.export = Button(self.left_column,
                             text='Export',
                             image=load_png('export'),
                             compound=LEFT)
        self.export.grid(row=2, sticky=NE)

        # Delete saved backup
        self.delete = Button(self.left_column,
                             text='Delete',
                             image=load_png('delete'),
                             compound=LEFT)
        self.delete.grid(row=3, sticky=NE)

        self.margin = Label(self.left_column)
        self.margin.grid(row=4, sticky=NE)

        # Go back
        self.back = Button(self.left_column,
                           text='Back',
                           image=load_png('back'),
                           compound=LEFT,
                           command=self.go_back)
        self.back.grid(row=5, sticky=NE)


        # Right column
        self.right_column = Frame(self)
        self.right_column.grid(row=1, column=1, sticky=NSEW)

        # Let this column (0) expand and contract with the window
        self.right_column.columnconfigure(0, weight=1)

        # Entity card showing stats
        self.entity_card = EntityCard(self.right_column,
                                      entity=self.entity,
                                      padding=16)
        self.entity_card.grid(row=0, sticky=EW)

        # Right bottom column
        self.bottom_column = Frame(self.right_column, padding=(0, 16, 0, 0))
        self.bottom_column.grid(row=1, sticky=EW)

        # Let this column (0) also expand and contract with the window
        self.bottom_column.columnconfigure(0, weight=1)

        # Estimated time left
        self.etl = Label(self.bottom_column,
                         text='Estimated time left: {}'
                         .format(self.backuper.metadata.get('etl', '???')))
        self.etl.grid(row=0, sticky=W)

        # Download progress bar
        self.progress = Progressbar(self.bottom_column)
        self.progress.grid(row=1, sticky=EW)

        # Downloaded messages/total messages
        self.text_progress = Label(self.bottom_column,
                                      text='???/??? messages saved')
        self.text_progress.grid(row=2, sticky=E)

        # Keep a tuple with all the buttons for easy access
        self.buttons = (self.resume_pause, self.save_media, self.export, self.delete, self.back)

    def resume_pause_backup(self):
        if not self.backuper.backup_running:
            self.toggle_buttons(False, self.resume_pause)
            self.backuper.start_backup()
            self.resume_pause.config(text='Pause',
                                     image=load_png('pause'))
        else:
            self.backuper.stop_backup()
            self.resume_pause.config(text='Resume',
                                     image=load_png('resume'))
            self.toggle_buttons(True, self.resume_pause)

    def go_back(self):
        """Goes back to the previous (select dialog) window"""
        self.master.destroy()

        # Import the window here to avoid cyclic dependencies
        from gui.windows import SelectDialogWindow
        start_app(SelectDialogWindow)

    def toggle_buttons(self, enabled, do_not_toggle=None):
        """Toggles all the buttons to be either enabled or disabled, except do_not_toggle"""
        state = NORMAL if enabled else DISABLED
        for b in self.buttons:
            if b != do_not_toggle:
                b.config(state=state)

    def on_metadata_change(self):
        self.text_progress.config(text='{}/{} messages saved'
                                  .format(self.backuper.metadata['saved_msgs'],
                                          self.backuper.metadata['total_msgs']))

        self.progress.config(maximum=self.backuper.metadata['total_msgs'],
                             value=self.backuper.metadata['saved_msgs'])

        self.etl.config(text='Estimated time left: {}'.format(self.backuper.metadata['etl']))

        # If the backup finished (we have all the messages), toggle the pause button
        # The backup must also be running so we can stop it
        if (self.backuper.metadata['saved_msgs'] == self.backuper.metadata['total_msgs'] and
                self.backuper.backup_running):
            self.resume_pause_backup()
