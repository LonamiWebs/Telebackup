import tkinter as tk
import tkinter.ttk as ttk


def start_app(window_class, **args):
    root = tk.Tk()
    app = window_class(master=root, **args)
    # Configure the style we'll be using
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('Horizontal.TProgressbar', foreground='#0064d2', background='#0064d2')

    app.mainloop()
