import tkinter as tk


def start_app(window_class):
    root = tk.Tk()
    app = window_class(master=root)
    app.mainloop()
