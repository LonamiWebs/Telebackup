import tkinter as tk


class WelcomeWindow(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self.master.title("Telebackup")
        self.master.minsize(640, 320)
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
        self.backup_chat.pack()

        # Download media
        self.download_media = tk.Button(self,
                                        text='Download media from a backup')
        self.download_media.pack()

        # Export conversation
        self.export_html = tk.Button(self,
                                     text='Export a backup to HTML')
        self.export_html.pack()

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



    """
            self.hi_there = tk.Button(self)
            self.hi_there["text"] = "Hello World\n(click me)"
            self.hi_there["command"] = self.say_hi
            self.hi_there.pack(side="top")

            self.quit = tk.Button(self, text="QUIT", fg="red",
                                  command=self.master.destroy)
            self.quit.pack(side="bottom")

            self.scrollbar = tk.Scrollbar(self)
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.mylist = tk.Listbox(self, yscrollcommand=self.scrollbar.set)
            for line in range(100):
                self.mylist.insert(tk.END, "This is line number " + str(line))

            self.mylist.pack(side=tk.LEFT, fill=tk.BOTH)
            self.scrollbar.config(command=self.mylist.yview)
    """

    def say_hi(self):
        print("hi there, everyone!")
