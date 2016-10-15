import tkinter as tk


def start_app(window_class, **args):
    root = tk.Tk()
    app = window_class(master=root, **args)
    app.mainloop()
