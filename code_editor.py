import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

class CodeEditor:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Basic Code Editor")
        self._setup_widgets()
        self.file_path = None

    def _setup_widgets(self):
        self.text = tk.Text(self.root, wrap="none", undo=True)
        self.text.pack(fill="both", expand=True)

        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Find", command=self.find_text, accelerator="Ctrl+F")
        edit_menu.add_command(label="Replace", command=self.replace_text, accelerator="Ctrl+H")
        menubar.add_cascade(label="Edit", menu=edit_menu)

        self.root.config(menu=menubar)
        self.root.bind_all("<Control-n>", lambda event: self.new_file())
        self.root.bind_all("<Control-o>", lambda event: self.open_file())
        self.root.bind_all("<Control-s>", lambda event: self.save_file())
        self.root.bind_all("<Control-f>", lambda event: self.find_text())
        self.root.bind_all("<Control-h>", lambda event: self.replace_text())

    def new_file(self):
        if self._confirm_discard_changes():
            self.text.delete(1.0, tk.END)
            self.file_path = None
            self.root.title("Basic Code Editor")

    def open_file(self):
        if not self._confirm_discard_changes():
            return
        file_path = filedialog.askopenfilename()
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                self.text.delete(1.0, tk.END)
                self.text.insert(tk.END, content)
                self.file_path = file_path
                self.root.title(f"Basic Code Editor - {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")

    def save_file(self):
        if self.file_path:
            try:
                content = self.text.get(1.0, tk.END)
                with open(self.file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}")
        else:
            self.save_file_as()

    def save_file_as(self):
        file_path = filedialog.asksaveasfilename()
        if file_path:
            try:
                content = self.text.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                self.file_path = file_path
                self.root.title(f"Basic Code Editor - {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}")

    def _confirm_discard_changes(self) -> bool:
        return messagebox.askyesno("Confirm", "Discard current changes?")

    def find_text(self):
        query = simpledialog.askstring("Find", "Enter text to find:")
        if query:
            start_pos = self.text.search(query, "1.0", stopindex=tk.END)
            self.text.tag_remove("find", "1.0", tk.END)
            if start_pos:
                end_pos = f"{start_pos}+{len(query)}c"
                self.text.tag_add("find", start_pos, end_pos)
                self.text.tag_config("find", background="yellow")
                self.text.see(start_pos)
            else:
                messagebox.showinfo("Find", "Text not found")

    def replace_text(self):
        query = simpledialog.askstring("Replace", "Enter text to find:")
        if query is None:
            return
        replacement = simpledialog.askstring("Replace", "Enter replacement text:")
        if replacement is None:
            return
        content = self.text.get("1.0", tk.END)
        new_content = content.replace(query, replacement)
        if content == new_content:
            messagebox.showinfo("Replace", "Text not found")
            return
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", new_content)


def main():
    root = tk.Tk()
    editor = CodeEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
