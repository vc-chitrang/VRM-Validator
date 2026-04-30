import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


class FileSelector(ttk.Frame):
    def __init__(self, master, browse_callback, **kwargs):
        super().__init__(master, **kwargs)

        self.columnconfigure(1, weight=1)

        self.label = ttk.Label(self, text="Model File")
        self.label.grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(self, textvariable=self.path_var, state="readonly")
        self.path_entry.grid(row=0, column=1, sticky="ew")

        self.browse_button = ttk.Button(self, text="Browse File", command=browse_callback)
        self.browse_button.grid(row=0, column=2, padx=(8, 0))

    def set_path(self, path: str) -> None:
        self.path_var.set(path)

    def get_path(self) -> str:
        return self.path_var.get()


class ActionButtons(ttk.Frame):
    def __init__(self, master, validate_callback, convert_callback, save_report_callback, **kwargs):
        super().__init__(master, **kwargs)

        self.validate_button = ttk.Button(self, text="Validate Model", command=validate_callback)
        self.validate_button.grid(row=0, column=0, padx=(0, 8))

        self.convert_button = ttk.Button(self, text="Convert to VRM", command=convert_callback)
        self.convert_button.grid(row=0, column=1, padx=(0, 8))

        self.save_button = ttk.Button(self, text="Save Report", command=save_report_callback)
        self.save_button.grid(row=0, column=2)

    def set_busy(self, is_busy: bool) -> None:
        state = "disabled" if is_busy else "normal"
        self.validate_button.config(state=state)
        self.convert_button.config(state=state)
        self.save_button.config(state=state)

    def set_convert_enabled(self, enabled: bool) -> None:
        self.convert_button.config(state="normal" if enabled else "disabled")

    def set_save_enabled(self, enabled: bool) -> None:
        self.save_button.config(state="normal" if enabled else "disabled")


class ReportPanel(ttk.LabelFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, text="Validation Report", **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.text = ScrolledText(self, wrap="word", height=10)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.text.configure(bg="#2b2d31", fg="#f2f2f2", insertbackground="#f2f2f2")
        self.text.config(state="disabled")

    def set_text(self, content: str) -> None:
        self.text.config(state="normal")
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, content)
        self.text.config(state="disabled")


class LogPanel(ttk.LabelFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, text="Logs", **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.text = ScrolledText(self, wrap="word", height=14)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.text.configure(bg="#2b2d31", fg="#f2f2f2", insertbackground="#f2f2f2")
        self.text.config(state="disabled")

    def append(self, line: str) -> None:
        self.text.config(state="normal")
        self.text.insert(tk.END, f"{line}\n")
        self.text.see(tk.END)
        self.text.config(state="disabled")

    def clear(self) -> None:
        self.text.config(state="normal")
        self.text.delete("1.0", tk.END)
        self.text.config(state="disabled")
