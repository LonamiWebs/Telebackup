import tkinter as tk


class WelcomeWindow(tk.Frame):
    def __init__(self, master=None):
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
                                     text='Backup a conversation',
                                     command=self.show_select_dialog)
        self.backup_chat.pack(fill=tk.X)

        # Download media
        self.download_media = tk.Button(self,
                                        text='Download media from a backup')
        self.download_media.pack(fill=tk.X)

        # Export conversation
        self.export_html = tk.Button(self,
                                     text='Export a backup to HTML')
        self.export_html.pack(fill=tk.X)

    def destroy_widgets(self):
        self.welcome.destroy()
        self.backup_chat.destroy()
        self.download_media.destroy()
        self.export_html.destroy()

    def show_select_dialog(self):
        self.destroy_widgets()

        from gui.windows.select_dialog import SelectDialogWindow
        app = SelectDialogWindow(master=self)
        app.mainloop()

    def say_hi(self):
        print("hi there, everyone!")
