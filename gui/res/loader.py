import tkinter as tk


loaded_images = {}


def load_png(name):
    """Loads a .png PhotoImage given its name"""
    if name in loaded_images:
        return loaded_images[name]
    else:
        loaded_images[name] = tk.PhotoImage(file='gui/res/png/{}.png'.format(name))
        return loaded_images[name]
