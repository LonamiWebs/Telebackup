from os.path import abspath
from tkinter import *
from tkinter.messagebox import showinfo, askquestion
from tkinter.ttk import *

from threading import Thread

from backuper import Backuper
from exporter.exporter import Exporter

from gui import start_app
from gui.res import load_png
from gui.widgets import EntityCard, ToggleButton
from gui.windows import SelectMediaDialog

from utils import get_cached_client, sanitize_string, size_to_str
from telethon.utils import get_display_name


class BackupWindow(Frame):
    def __init__(self, master=None, **args):
        super().__init__(master)

        # Save our entity and its display
        self.entity = args['entity']
        self.display = sanitize_string(get_display_name(self.entity))

        # Get a cached client and initialize a backuper instance with it
        self.client = get_cached_client()
        self.backuper = Backuper(self.client, self.entity)
        self.backuper.on_metadata_change = self.on_metadata_change

        # Set up the frame itself
        self.master.title('Backup with {}'.format(self.display))
        self.pack(padx=16, pady=16)
        self.create_widgets()

        # Download the profile picture in a different thread
        Thread(target=self.dl_propic).start()

    def dl_propic(self):
        self.backuper.update_total_messages()
        self.entity_card.update_profile_photo(self.backuper.backup_propic())

        # Fire the on_metadata to update some visual fields (such as current backup progress)
        self.on_metadata_change()

    #region Widgets setup

    def create_widgets(self):
        #                                                           Title label
        self.title = Label(self,
                           text='Backup generation for {}'.format(self.display),
                           font='-weight bold -size 18',
                           padding=(16, 0, 16, 16))
        self.title.grid(row=0, columnspan=2)

        #                                                           -- Left column
        self.left_column = Frame(self, padding=(16, 0))
        self.left_column.grid(row=1, column=0, sticky=NE)

        #                                                           Resume/pause backup download
        self.resume_pause = ToggleButton(self.left_column,
                                         text='Resume',
                                         image=load_png('resume'),
                                         checked_text='Pause',
                                         checked_image=load_png('pause'),
                                         on_toggle=self.resume_pause_backup)
        self.resume_pause.grid(row=0, sticky=NE)

        #                                                           Save (download) media
        self.save_media = ToggleButton(self.left_column,
                                       text='Save media',
                                       image=load_png('download'),
                                       checked_text='Cancel',
                                       checked_image=load_png('cancel'),
                                       on_toggle=self.prompt_save_media)
        self.save_media_dialog_shown = False
        self.save_media.grid(row=1, sticky=N)

        #                                                           Export backup
        self.export = Button(self.left_column,
                             text='Export',
                             image=load_png('export'),
                             compound=LEFT,
                             command=self.do_export)
        self.export.grid(row=2, sticky=NE)

        #                                                           Delete saved backup
        self.delete = Button(self.left_column,
                             text='Delete',
                             image=load_png('delete'),
                             compound=LEFT,
                             command=self.delete_backup)
        self.delete.grid(row=3, sticky=NE)

        #                                                           Margin label
        self.margin = Label(self.left_column)
        self.margin.grid(row=4, sticky=NE)

        #                                                           Go back
        self.back = Button(self.left_column,
                           text='Back',
                           image=load_png('back'),
                           compound=LEFT,
                           command=self.go_back)
        self.back.grid(row=5, sticky=NE)

        #                                                           -- Right column
        self.right_column = Frame(self)
        self.right_column.grid(row=1, column=1, sticky=NSEW)
        # Let this column (0) expand and contract with the window
        self.right_column.columnconfigure(0, weight=1)

        #                                                           Entity card showing stats
        self.entity_card = EntityCard(self.right_column,
                                      entity=self.entity,
                                      padding=16)
        self.entity_card.grid(row=0, sticky=EW)

        #                                                           Right bottom column
        self.bottom_column = Frame(self.right_column,
                                   padding=(0, 16, 0, 0))
        self.bottom_column.grid(row=1, sticky=EW)
        # Let this column (0) also expand and contract with the window
        self.bottom_column.columnconfigure(0, weight=1)

        #                                                           Estimated time left
        self.etl = Label(self.bottom_column,
                         text='Estimated time left: {}'
                         .format(self.backuper.metadata.get('etl', '???')))
        self.etl.grid(row=0, sticky=W)

        #                                                           Download progress bar
        self.progress = Progressbar(self.bottom_column)
        self.progress.grid(row=1, sticky=EW)

        #                                                           Downloaded messages/total messages
        self.text_progress = Label(self.bottom_column,
                                      text='???/??? messages saved')
        self.text_progress.grid(row=2, sticky=E)

        # Keep a tuple with all the buttons for easy access
        self.buttons = (self.resume_pause, self.save_media, self.export, self.delete, self.back)

    #endregion

    #region Button actions

    def resume_pause_backup(self):
        """Resumes or pauses the backup, depending on resume_pause current state"""
        if self.resume_pause.is_checked:
            # The button is now checked (paused → resumed)
            self.toggle_buttons(False, self.resume_pause)
            self.backuper.start_backup()
        else:
            # The button is now unchecked (resumed → paused)
            self.backuper.stop_backup()
            self.toggle_buttons(True, self.resume_pause)

    def prompt_save_media(self):
        """Prompts the save media dialog, or cancels the current media download"""
        if self.save_media_dialog_shown:
            return

        if self.save_media.is_checked:
            self.toggle_buttons(False, self.save_media)

            self.save_media_dialog_shown = True
            result = SelectMediaDialog.show_dialog(self,
                                                   size_calculator=self.backuper.calculate_download_size)
            self.save_media_dialog_shown = False

            # Start the backup or restore the buttons depending on action
            if result:
                # Set a callback on the resulting dictionary
                result['progress_callback'] = lambda c, t, etl: \
                    self.update_labels(c, t, 'media downloaded', etl=etl,
                                       value_representation=size_to_str)

                self.backuper.start_media_backup(**result)
            else:
                self.save_media.toggle(checked=False)
        else:
            self.backuper.stop_backup()
            self.toggle_buttons(True, self.save_media)

    def delete_backup(self):
        """Asks the user whether to delete the current backup and goes back to the previous window"""
        do_delete = askquestion('Please read carefully',
                                'Deleting the backup will completely remove the backup directory '
                                'with the selected dialog, INCLUDING ANY FILE YOU PLACED IN IT. '
                                'Please make sure you did NOT put any personal file under:\n{}.\n\n'
                                'Also note that this will NOT delete any message from Telegram. '
                                'Do you wish to continue?'.format(abspath(self.backuper.backup_dir)),
                                icon='warning')
        if do_delete == 'yes':
            self.backuper.delete_backup()
            showinfo('Backup deleted',
                     'Your backup with {} has been completely removed. '
                     'You will now go back to the dialogs window.'.format(self.display))
            self.go_back()

    def do_export(self):
        """Runs the export process"""
        exporter = Exporter(self.backuper.files['database'], self.display)
        self.toggle_buttons(enabled=False)
        exporter.export(callback=self.on_export_callback)

    def go_back(self):
        """Goes back to the previous (select dialog) window"""
        self.master.destroy()

        # Import the window here to avoid cyclic dependencies
        from gui.windows import SelectDialogWindow
        start_app(SelectDialogWindow)

    #endregion

    #region Events

    def on_metadata_change(self):
        """Occurs when the backuper's metadata changes"""
        self.update_labels(current=self.backuper.metadata['saved_msgs'],
                           total=self.backuper.metadata['total_msgs'],
                           progress_type='messages saved',
                           etl=self.backuper.metadata['etl'])

        # Do we have all the messages?
        have_all = self.backuper.metadata['saved_msgs'] == self.backuper.metadata['total_msgs']

        # If the backup finished (we have all the messages), toggle the pause button
        # The backup must also be running so we can stop it
        if have_all and self.backuper.backup_running:
            self.resume_pause.toggle(False)

    def on_export_callback(self, progress):
        """Occurs when the exporters progress changes"""
        self.update_labels(current=progress['exported'],
                           total=progress['total'],
                           progress_type='messages exported',
                           etl=progress['etl'])

        if progress['exported'] == progress['total']:
            self.toggle_buttons(enabled=True)

    def update_labels(self, current, total, progress_type, etl, value_representation=str):
        """Updates the labels and progress given current/total and estimated time left.
           Progress type should be "messages saved", "messages exported", etc.

           value_representation should be a function taking a float value and returning a string"""
        self.text_progress.config(text='{}/{} {}{}'.format(value_representation(current),
                                                           value_representation(total),
                                                           progress_type,
                                                           ' (completed)' if (current == total) else ''))
        self.progress.config(maximum=total, value=current)

        # Strip extra 0's from the end of the string (we don't want "1.00000", for example)
        etl = str(etl).rstrip('0')
        # However maybe we stripped 0 seconds and now we have "0:00:", so fix that too
        if etl[-1] == ':':
            etl += '00'

        self.etl.config(text='Estimated time left: {}'.format(etl))

    #endregion

    #region Utilities

    def toggle_buttons(self, enabled, do_not_toggle=None):
        """Toggles all the buttons to be either enabled or disabled, except do_not_toggle"""
        state = NORMAL if enabled else DISABLED
        for b in self.buttons:
            if b != do_not_toggle:
                b.config(state=state)

    #endregion
