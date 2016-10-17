import tkinter as tk
import tkinter.ttk as ttk


def start_app(window_class, **args):
    root = tk.Tk()
    app = window_class(master=root, **args)
    ttk.Style().theme_use('clam')
    app.mainloop()
