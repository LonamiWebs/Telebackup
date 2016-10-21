import tkinter as tk


loaded_images = []


def load_png(name):
    """Loads a .png PhotoImage given its name"""
    # Always load a new PhotoImage (previous maybe are destroyed)
    image = tk.PhotoImage(file='gui/res/png/{}.png'.format(name))
    # Append the image so it doesn't get garbage collected
    loaded_images.append(image)
    return image


def clear_png():
    """Clears the loaded .png references"""
    loaded_images.clear()
