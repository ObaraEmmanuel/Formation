#!/usr/bin/python3

import os
import shelve
from tkinter import Label, Tk, Frame

from PIL import Image, ImageTk


PATH = "../hoverset/data/image"


class ImageView(Label):

    def __init__(self, master, image: Image):
        super().__init__(master, bg="#5a5a5a")
        self.image = image
        self.image.thumbnail((40, 40), Image.LANCZOS)
        self.config(width=image.size[0], height=image.size[1])
        self._rendered = ImageTk.PhotoImage(image=self.image)
        self.config(image=self._rendered)
        self.bind("<Enter>", lambda _: self.config(bg="#3a3a3a", fg="green"))
        self.bind("<Leave>", lambda _: self.config(bg="#5a5a5a", fg="white"))


def recolor(color1, color2, image) -> Image:
    image = image.copy()
    pix = image.load()
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            if pix[x, y] == color1:
                image.putpixel((x, y), color2)
    return image


def add_image(image: Image, name) -> None:
    with shelve.open(PATH) as dat:
        dat[name] = image


def get_image(name, color):
    with shelve.open(PATH) as dat:
        img = dat[name]
        return recolor((255, 255, 255, 255), color, img)


def load_all(parent):
    columns = 15
    column = 0
    row = 0
    with shelve.open(PATH) as db:
        for name in db:
            view = ImageView(parent, db[name])
            view.grid(row=row, column=column)
            column += 1
            if column == columns:
                column = 0
                row += 1


def save_core():
    db = shelve.open(PATH)
    try:
        for file in os.listdir("core"):
            if file.endswith(".png"):
                img = Image.open(os.path.join("core", file))
                db[file.split(".")[0]] = img
    except Exception as e:
        print(e)
    finally:
        db.close()


def save_icons():
    path = "icons"
    db = shelve.open(PATH)
    try:
        for file in os.listdir(path):
            if file.endswith(".png"):
                img = Image.open(os.path.join(path, file))
                img.thumbnail((86, 86), Image.LANCZOS)
                key = file.split(".")[0]
                new_key = "".join(["_", key])
                db[new_key] = img
                if key in db:
                    del db[key]
    except Exception as e:
        print(e)
    finally:
        db.close()


if __name__ == '__main__':
    root = Tk()
    save_icons()
    save_core()
    f = Frame(root, bg="#5a5a5a", width=400, height=400)
    f.pack(fill="both", expand=True)
    f.grid_propagate(1)
    load_all(f)
    root.mainloop()
