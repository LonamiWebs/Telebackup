import tkinter as tk

class SelectDialogWindow(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.pack()
        self.create_widgets()
        self.update_conversation_list()

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
        self.conversation_list.pack()

        self.search_box = tk.Entry()
        self.search_box.pack()

        self.search_box['textvariable'] = 'hi'
        self.search_box.textvariable = 'lol'

        # and here we get a callback when the user hits return.
        # we will have the program print out the value of the
        # application variable when the user hits return
        self.search_box.bind('<Key>', self.search)

        # Search box

    def update_conversation_list(self):
        items = ['Hello', 'Hella', 'Yay', 'Yoy', 'You', 'Kek', 'Lol', 'Loool', 'Lool']

        search = self.search_box.get().lower()
        self.conversation_list.delete(0, tk.END)

        for item in items:
            if search in item.lower():
                self.conversation_list.insert(tk.END, item)

        pass

    def search(self, *args):
        self.update_conversation_list()

    def say_hi(self):
        print("hi there, everyone!")
