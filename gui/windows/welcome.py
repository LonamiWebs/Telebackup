import tkinter as tk

from gui.main import start_app
from gui.windows.select_dialog import SelectDialogWindow
from gui.res.loader import load_png


class WelcomeWindow(tk.Frame):
    def __init__(self, master=None, **args):
        super().__init__(master)

        self.master.title("Telebackup")
        self.master.maxsize(1000, 480)

        self.pack()
        self.create_widgets()

    def create_widgets(self):
        # Welcome label
        self.welcome = tk.Label(self,
                                text='Welcome to Telebackup! Please select an option:')
        self.welcome.grid(row=0)

        # Backup chat
        self.backup_chat = tk.Button(self,
                                     command=self.show_select_dialog,
                                     text='Backup a conversation',
                                     image=load_png('conversation'),
                                     compound=tk.LEFT)
        self.backup_chat.grid(row=1, sticky=tk.EW)

        # Download media
        self.download_media = tk.Button(self,
                                        text='Download media from a backup',
                                        image=load_png('media'),
                                        compound=tk.LEFT)
        self.download_media.grid(row=2, sticky=tk.EW)

        # Export conversation
        self.export_html = tk.Button(self,
                                     text='Export a backup to HTML',
                                        image=load_png('html'),
                                        compound=tk.LEFT)
        self.export_html.grid(row=3, sticky=tk.EW)

        # Exit application
        self.exit = tk.Button(self,
                              command=self.master.destroy,
                              text='Exit application',
                              image=load_png('exit'),
                              compound=tk.LEFT)
        self.exit.grid(row=4, sticky=tk.EW)

    def show_select_dialog(self):
        self.master.destroy()
        start_app(SelectDialogWindow)
