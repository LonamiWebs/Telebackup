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
        self.welcome.pack()

        # Backup chat
        self.backup_chat = tk.Button(self,
                                     command=self.show_select_dialog,
                                     text='Backup a conversation',
                                     image=load_png('conversation'),
                                     compound=tk.LEFT)
        self.backup_chat.pack(fill=tk.X)

        # Download media
        self.download_media = tk.Button(self,
                                        text='Download media from a backup',
                                        image=load_png('media'),
                                        compound=tk.LEFT)
        self.download_media.pack(fill=tk.X)

        # Export conversation
        self.export_html = tk.Button(self,
                                     text='Export a backup to HTML',
                                        image=load_png('html'),
                                        compound=tk.LEFT)
        self.export_html.pack(fill=tk.X)

        # Exit application
        self.exit = tk.Button(self,
                              command=self.master.destroy,
                              text='Exit application',
                              image=load_png('exit'),
                              compound=tk.LEFT)
        self.exit.pack(fill=tk.X)

    def show_select_dialog(self):
        self.master.destroy()
        start_app(SelectDialogWindow)


    def say_hi(self):
        print("hi there, everyone!")
