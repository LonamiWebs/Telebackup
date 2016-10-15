import tkinter as tk
from gui.widgets.better_entry import BetterEntry

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
        self.info = tk.Label(self, textvariable=self.info_content)
        self.info.grid(row=0)

        self.code = BetterEntry(self,
                                max_length=code_length,
                                on_change=self.code_on_change,
                                paste_filter=self.code_paste_filter)
        self.code.grid(row=1)

        # Next step
        self.next = tk.Button(self,
                              text='Validate code',
                              command=self.login,
                              state=tk.DISABLED)
        self.next.grid(row=2)

    def code_on_change(self):
        """Event listener for when the code changes"""
        code = self.code.get()

        # Then check if it's right (or the user is authorized)
        if (len(code) == code_length and str.isdigit(code) or
                self.client.is_user_authorized()):
            self.next.config(state=tk.NORMAL)
        else:
            self.next.config(state=tk.DISABLED)

    def code_paste_filter(self, clipboard):
        """Clipboard filter for the Telegram code"""
        result = []
        # Iterate over the clipboard to find the digits
        for char in self.clipboard_get():
            if str.isdigit(char):
                result.append(char)
                if len(result) == code_length:
                    break

        return ''.join(result)


    def login(self):
        """Starts the login process"""
        if not self.client.is_user_authorized():
            self.code.disable()
            code = self.code.get()
            self.info_content.set('Logging in... please wait.')
            self.client.sign_in(self.phone, code)
            self.info_content.set('Logged in successfully! Click Next to continue.')
            self.next.config(text='Next')
        else:
            self.master.destroy()
