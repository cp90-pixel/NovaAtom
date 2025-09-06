import os
import sys
import re
import keyword
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText
import subprocess
import threading

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
        edit_menu.add_command(label="Go to Definition", command=self.goto_definition, accelerator="F12")
        menubar.add_cascade(label="Edit", menu=edit_menu)

        terminal_menu = tk.Menu(menubar, tearoff=0)
        terminal_menu.add_command(label="Open Terminal", command=self.open_terminal, accelerator="Ctrl+T")
        menubar.add_cascade(label="Terminal", menu=terminal_menu)

        self.root.config(menu=menubar)
        self.root.bind_all("<Control-n>", lambda event: self.new_file())
        self.root.bind_all("<Control-o>", lambda event: self.open_file())
        self.root.bind_all("<Control-s>", lambda event: self.save_file())
        self.root.bind_all("<Control-f>", lambda event: self.find_text())
        self.root.bind_all("<Control-h>", lambda event: self.replace_text())
        self.root.bind_all("<Control-t>", lambda event: self.open_terminal())
        self.root.bind_all("<F12>", lambda event: self.goto_definition())
        self.root.bind_all("<Control-space>", lambda event: self.show_autocomplete())

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

    def goto_definition(self):
        """Jump to the definition of the word under the cursor."""
        word = self._get_current_word()
        if not word:
            messagebox.showinfo("Go to Definition", "No symbol selected")
            return

        pattern = re.compile(rf"^\s*(def|class)\s+{re.escape(word)}\b")
        lines = self.text.get("1.0", tk.END).splitlines()
        for i, line in enumerate(lines, start=1):
            if pattern.search(line):
                self.text.tag_remove("definition", "1.0", tk.END)
                start = f"{i}.0"
                end = f"{i}.0 lineend"
                self.text.tag_add("definition", start, end)
                self.text.tag_config("definition", background="lightblue")
                self.text.mark_set(tk.INSERT, start)
                self.text.see(start)
                return
        messagebox.showinfo("Go to Definition", f"Definition for '{word}' not found")

    def _get_current_word(self) -> str:
        index = self.text.index(tk.INSERT)
        start = self.text.index(f"{index} wordstart")
        end = self.text.index(f"{index} wordend")
        word = self.text.get(start, end).strip()
        return word

    def _get_current_prefix(self) -> str:
        index = self.text.index(tk.INSERT)
        start = self.text.index(f"{index} wordstart")
        prefix = self.text.get(start, index)
        return prefix

    def show_autocomplete(self):
        prefix = self._get_current_prefix()
        suggestions = set(keyword.kwlist)
        document_words = re.findall(r"\b\w+\b", self.text.get("1.0", tk.END))
        suggestions.update(document_words)
        matches = sorted({s for s in suggestions if s.startswith(prefix) and s != prefix})
        if not matches:
            return
        if len(matches) == 1:
            self.text.insert(tk.INSERT, matches[0][len(prefix):])
            return
        self._open_autocomplete_window(matches, prefix)

    def _open_autocomplete_window(self, matches, prefix):
        if hasattr(self, "autocomplete_window") and self.autocomplete_window.winfo_exists():
            self.autocomplete_window.destroy()
        bbox = self.text.bbox(tk.INSERT)
        if not bbox:
            return
        x, y, width, height = bbox
        x += self.text.winfo_rootx()
        y += self.text.winfo_rooty() + height
        self.autocomplete_window = tk.Toplevel(self.root)
        self.autocomplete_window.wm_overrideredirect(True)
        self.autocomplete_window.geometry(f"+{x}+{y}")
        listbox = tk.Listbox(self.autocomplete_window, height=min(6, len(matches)))
        for m in matches:
            listbox.insert(tk.END, m)
        listbox.pack()
        listbox.bind("<Return>", lambda event: self._insert_autocomplete(prefix))
        listbox.bind("<Double-Button-1>", lambda event: self._insert_autocomplete(prefix))
        listbox.bind("<Escape>", lambda event: self.autocomplete_window.destroy())
        listbox.focus_set()
        self.autocomplete_listbox = listbox

    def _insert_autocomplete(self, prefix):
        selection = self.autocomplete_listbox.curselection()
        if selection:
            value = self.autocomplete_listbox.get(selection[0])
            self.text.insert(tk.INSERT, value[len(prefix):])
        self.autocomplete_window.destroy()

    def open_terminal(self):
        if hasattr(self, "terminal_window") and self.terminal_window.winfo_exists():
            self.terminal_window.deiconify()
            self.terminal_entry.focus()
            return

        self.terminal_window = tk.Toplevel(self.root)
        self.terminal_window.title("Terminal")

        self.terminal_output = ScrolledText(self.terminal_window, wrap="word")
        self.terminal_output.pack(fill="both", expand=True)

        entry_frame = tk.Frame(self.terminal_window)
        entry_frame.pack(fill="x")

        self.terminal_entry = tk.Entry(entry_frame)
        self.terminal_entry.pack(side="left", fill="x", expand=True)
        self.terminal_entry.bind("<Return>", lambda event: self.run_command())

        run_button = tk.Button(entry_frame, text="Run", command=self.run_command)
        run_button.pack(side="right")

    def run_command(self):
        command = self.terminal_entry.get()
        if not command.strip():
            return
        self.terminal_output.insert(tk.END, f"$ {command}\n")
        self.terminal_entry.delete(0, tk.END)

        def worker():
            try:
                completed = subprocess.run(
                    command, shell=True, capture_output=True, text=True
                )
                output = completed.stdout + completed.stderr
            except Exception as e:
                output = str(e) + "\n"
            self.terminal_output.insert(tk.END, output)
            self.terminal_output.see(tk.END)

        threading.Thread(target=worker, daemon=True).start()


def main():
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        print("No display detected. This application requires a graphical display.")
        return
    try:
        root = tk.Tk()
    except tk.TclError:
        print(
            "Unable to initialize Tk. Ensure a graphical display is available."
        )
        return
    editor = CodeEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
