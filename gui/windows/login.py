import tkinter as tk
from gui.res.loader import load_png


# Telegram code length
code_length = 5


class LoginWindow(tk.Frame):
    def __init__(self, master=None, **args):
        super().__init__(master)

        self.client = args['client']
        self.phone = args['phone']

        self.master.title("Telebackup")
        self.master.maxsize(1000, 480)

        self.pack()
        self.create_widgets()

    def create_widgets(self):
        # These have a single column
        # Welcome label
        self.info_content = tk.StringVar()
        self.info_content.set("We've sent you a code via Telegram since this is the first time.\n"
                              "Please enter it below to login (in order to use this program):")
        self.info = tk.Label(self, textvariable=self.info_content, padx=10, pady=10)
        self.info.pack()

        # Next step
        self.next = tk.Button(self,
                              text='Validate code',
                              command=self.login,
                              state=tk.DISABLED)
        self.next.pack(side=tk.BOTTOM, fill=tk.X)

        # These have more than one column
        # Paste code button
        self.paste = tk.Button(self,
                               image=load_png('clipboard'),
                               width='16',
                               height='16',
                               command=self.paste_code)
        self.paste.pack(side=tk.RIGHT, anchor=tk.NW, pady=10)

        # Erase code button
        self.erase = tk.Button(self,
                               image=load_png('backspace'),
                               width='16',
                               height='16',
                               command=self.clear_code)
        self.erase.pack(side=tk.RIGHT, anchor=tk.NW, pady=10)

        # Backup chat
        self.code = tk.Entry(self)
        self.code.bind('<KeyRelease>', self.validate_code_input)
        self.code.pack(fill=tk.X, pady=10)


    def validate_code_input(self, event=None):
        """Validates the code input to enable the Next button"""

        # First ensure its length is inside the bounds
        code = self.code.get()
        if len(code) > code_length:
            self.code.delete(code_length, tk.END)
            code = self.code.get()

        # Then check if it's right (or the user is authorized)
        if (len(code) == code_length and str.isdigit(code) or
                self.client.is_user_authorized()):
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
        if not self.client.is_user_authorized():
            code = self.code.get()
            self.info_content.set('Logging in... please wait.')
            self.client.sign_in(self.phone, code)
            self.info_content.set('Logged in successfully! Click Next to continue.')
            self.next.config(text='Next')
        else:
            self.master.destroy()
