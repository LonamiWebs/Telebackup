import tkinter as tk
from gui.res.loader import load_png


# Telegram code length
code_length = 5


class LoginWindow(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self.master.title("Telebackup")
        self.master.maxsize(1000, 480)

        self.pack()
        self.create_widgets()

    def create_widgets(self):
        # Welcome label
        self.info_content = tk.StringVar()
        self.info_content.set("We've sent you a code via Telegram since this is the first time.\n"
                              "Please enter it below to login (in order to use this program):")
        self.info = tk.Label(self, textvariable=self.info_content)
        self.info.pack()

        # Paste code button
        self.paste = tk.Button(self,
                               image=load_png('clipboard'),
                               width='16',
                               height='16',
                               command=self.paste_code)
        self.paste.pack(side=tk.RIGHT, anchor=tk.N)

        # Erase code button
        self.erase = tk.Button(self,
                               image=load_png('backspace'),
                               width='16',
                               height='16',
                               command=self.clear_code)
        self.erase.pack(side=tk.RIGHT, anchor=tk.N)

        # Backup chat
        self.code = tk.Entry(self)
        self.code.bind('<KeyRelease>', self.validate_code_input)
        self.code.pack()

        # Next step
        self.next = tk.Button(self,
                              text='Validate code',
                              command=self.login,
                              state=tk.DISABLED)
        self.next.pack()

    def validate_code_input(self, event=None):
        """Validates the code input to enable the Next button"""

        # First ensure its length is inside the bounds
        code = self.code.get()
        if len(code) > code_length:
            self.code.delete(code_length, tk.END)
            code = self.code.get()

        # Then check if it's right
        if len(code) == code_length and str.isdigit(code):
            self.next.config(state=tk.NORMAL)
        else:
            self.next.config(state=tk.DISABLED)

    def clear_code(self):
        self.code.delete(0, tk.END)
        self.next.config(state=tk.DISABLED)

    def paste_code(self):
        self.clear_code()
        left = code_length
        # Iterate over the clipboard to find the digits
        for char in self.clipboard_get():
            if str.isdigit(char):
                self.code.insert(tk.END, char)
                # Check if we've pasted 5 digits yet
                left -= 1
                if left == 0:
                    break

        # Validate the code input
        self.validate_code_input()

    def login(self):
        """Starts the login process"""
        code = self.code.get()
        code = int(code)
        self.info_content.set('Logging in... please wait.')
