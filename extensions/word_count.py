import re
from tkinter import messagebox


def register(editor):
    def count_words():
        content = editor.text.get("1.0", "end")
        words = re.findall(r"\b\w+\b", content)
        messagebox.showinfo("Word Count", f"{len(words)} words")

    editor.add_extension_command("Word Count", count_words)
