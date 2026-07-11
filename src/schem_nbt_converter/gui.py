from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .errors import ConversionError
from .writer import convert_file

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:  # Drag and drop remains optional when TkDND is unavailable.
    DND_FILES = None
    TkinterDnD = None


COLORS = {
    "background": "#0b1120",
    "card": "#111827",
    "card_alt": "#172033",
    "field": "#0f172a",
    "border": "#263449",
    "text": "#f8fafc",
    "muted": "#94a3b8",
    "accent": "#3b82f6",
    "accent_hover": "#2563eb",
    "danger": "#ef4444",
    "danger_hover": "#dc2626",
    "success": "#22c55e",
    "selection": "#1d4ed8",
}


class ConverterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Schem & Litematic to NBT")
        self.root.geometry("1120x760")
        self.root.minsize(900, 640)
        self.root.configure(background=COLORS["background"])

        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self.running = False

        # Maps each input file to the folder that was imported by the user.
        # This lets the converter reproduce the same relative directory tree.
        self.source_roots: dict[str, Path | None] = {}

        desktop = Path.home() / "Desktop"
        default_output = (desktop if desktop.is_dir() else Path.home()) / "nbt_output"
        self.output_var = tk.StringVar(value=str(default_output))
        self.split_var = tk.BooleanVar(value=True)
        self.air_var = tk.BooleanVar(value=True)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.preserve_tree_var = tk.BooleanVar(value=True)
        self.max_size_var = tk.IntVar(value=48)
        self.status_var = tk.StringVar(value="Ready")
        self.file_count_var = tk.StringVar(value="0 files")
        self.progress_text_var = tk.StringVar(value="0 / 0")

        self._configure_fonts()
        self._configure_styles()
        self._build_ui()
        self._bind_shortcuts()
        self.root.after(100, self._poll_messages)

    def _configure_fonts(self) -> None:
        family = "Segoe UI" if sys.platform.startswith("win") else "DejaVu Sans"
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                font = tkfont.nametofont(name)
                font.configure(family=family, size=10)
            except tk.TclError:
                pass

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("App.TFrame", background=COLORS["background"])
        style.configure("Card.TFrame", background=COLORS["card"])
        style.configure("CardAlt.TFrame", background=COLORS["card_alt"])

        style.configure(
            "Title.TLabel",
            background=COLORS["background"],
            foreground=COLORS["text"],
            font=("Segoe UI", 24, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=COLORS["background"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=COLORS["card"],
            foreground=COLORS["text"],
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "CardText.TLabel",
            background=COLORS["card"],
            foreground=COLORS["muted"],
        )
        style.configure(
            "CardValue.TLabel",
            background=COLORS["card"],
            foreground=COLORS["text"],
        )
        style.configure(
            "Status.TLabel",
            background=COLORS["card"],
            foreground=COLORS["muted"],
        )
        style.configure(
            "Success.TLabel",
            background=COLORS["card"],
            foreground=COLORS["success"],
            font=("Segoe UI", 10, "bold"),
        )

        style.configure(
            "Primary.TButton",
            background=COLORS["accent"],
            foreground="#ffffff",
            borderwidth=0,
            focusthickness=0,
            focuscolor=COLORS["accent"],
            padding=(18, 11),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("active", COLORS["accent_hover"]), ("disabled", "#334155")],
            foreground=[("disabled", "#94a3b8")],
        )

        style.configure(
            "Secondary.TButton",
            background=COLORS["card_alt"],
            foreground=COLORS["text"],
            borderwidth=0,
            focusthickness=0,
            padding=(12, 8),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", COLORS["border"])],
        )

        style.configure(
            "Danger.TButton",
            background=COLORS["card_alt"],
            foreground="#fca5a5",
            borderwidth=0,
            focusthickness=0,
            padding=(12, 8),
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#3f1d29")],
            foreground=[("active", "#fecaca")],
        )

        style.configure(
            "Modern.TEntry",
            fieldbackground=COLORS["field"],
            foreground=COLORS["text"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["border"],
            darkcolor=COLORS["border"],
            insertcolor=COLORS["text"],
            padding=8,
        )
        style.map(
            "Modern.TEntry",
            bordercolor=[("focus", COLORS["accent"])],
            lightcolor=[("focus", COLORS["accent"])],
            darkcolor=[("focus", COLORS["accent"])],
        )

        style.configure(
            "Modern.TSpinbox",
            fieldbackground=COLORS["field"],
            foreground=COLORS["text"],
            arrowcolor=COLORS["muted"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["border"],
            darkcolor=COLORS["border"],
            insertcolor=COLORS["text"],
            padding=6,
        )

        style.configure(
            "Modern.TCheckbutton",
            background=COLORS["card"],
            foreground=COLORS["text"],
            indicatorbackground=COLORS["field"],
            indicatorforeground=COLORS["accent"],
            padding=(0, 2),
        )
        style.map(
            "Modern.TCheckbutton",
            background=[("active", COLORS["card"])],
            foreground=[("disabled", COLORS["muted"])],
            indicatorbackground=[("selected", COLORS["accent"]), ("active", COLORS["field"])],
        )

        style.configure(
            "Modern.Horizontal.TProgressbar",
            troughcolor=COLORS["field"],
            background=COLORS["accent"],
            bordercolor=COLORS["field"],
            lightcolor=COLORS["accent"],
            darkcolor=COLORS["accent"],
            thickness=9,
        )

        style.configure(
            "Vertical.TScrollbar",
            background=COLORS["card_alt"],
            troughcolor=COLORS["field"],
            bordercolor=COLORS["field"],
            arrowcolor=COLORS["muted"],
        )
        style.configure(
            "Horizontal.TScrollbar",
            background=COLORS["card_alt"],
            troughcolor=COLORS["field"],
            bordercolor=COLORS["field"],
            arrowcolor=COLORS["muted"],
        )

    def _card(self, parent: tk.Misc) -> tuple[tk.Frame, ttk.Frame]:
        border = tk.Frame(parent, background=COLORS["border"], padx=1, pady=1)
        inner = ttk.Frame(border, style="Card.TFrame", padding=16)
        inner.pack(fill="both", expand=True)
        return border, inner

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, style="App.TFrame", padding=20)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=3)
        outer.columnconfigure(1, weight=2)
        outer.rowconfigure(1, weight=1)

        header = ttk.Frame(outer, style="App.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)

        title_block = ttk.Frame(header, style="App.TFrame")
        title_block.grid(row=0, column=0, sticky="w")
        ttk.Label(title_block, text="Schem & Litematic to NBT", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_block,
            text="Batch-convert Minecraft Java schematics into vanilla structure files.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        badge = tk.Label(
            header,
            text="  VANILLA NBT  ",
            background="#132e52",
            foreground="#93c5fd",
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=6,
        )
        badge.grid(row=0, column=1, sticky="e")

        files_border, files_card = self._card(outer)
        files_border.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        files_card.columnconfigure(0, weight=1)
        files_card.rowconfigure(2, weight=1)

        files_header = ttk.Frame(files_card, style="Card.TFrame")
        files_header.grid(row=0, column=0, sticky="ew")
        files_header.columnconfigure(0, weight=1)
        ttk.Label(files_header, text="Input files", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.count_badge = tk.Label(
            files_header,
            textvariable=self.file_count_var,
            background=COLORS["card_alt"],
            foreground=COLORS["muted"],
            padx=9,
            pady=4,
            font=("Segoe UI", 9, "bold"),
        )
        self.count_badge.grid(row=0, column=1, sticky="e")

        dnd_text = "Drop files or folders below, or use the buttons."
        if DND_FILES is None:
            dnd_text += " Drag and drop is unavailable in this environment."
        ttk.Label(files_card, text=dnd_text, style="CardText.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 10)
        )

        list_container = tk.Frame(
            files_card,
            background=COLORS["field"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        list_container.grid(row=2, column=0, sticky="nsew")
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)

        self.file_list = tk.Listbox(
            list_container,
            selectmode=tk.EXTENDED,
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
            background=COLORS["field"],
            foreground=COLORS["text"],
            selectbackground=COLORS["selection"],
            selectforeground="#ffffff",
            font=("Consolas" if sys.platform.startswith("win") else "DejaVu Sans Mono", 9),
            relief="flat",
            exportselection=False,
        )
        self.file_list.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=(8, 0))
        v_scroll = ttk.Scrollbar(list_container, orient="vertical", command=self.file_list.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll = ttk.Scrollbar(list_container, orient="horizontal", command=self.file_list.xview)
        h_scroll.grid(row=1, column=0, sticky="ew", padx=(0, 0))
        self.file_list.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        if DND_FILES and hasattr(self.file_list, "drop_target_register"):
            self.file_list.drop_target_register(DND_FILES)
            self.file_list.dnd_bind("<<Drop>>", self._on_drop)

        file_buttons = ttk.Frame(files_card, style="Card.TFrame")
        file_buttons.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(file_buttons, text="Add files", style="Secondary.TButton", command=self._add_files).pack(
            side="left"
        )
        ttk.Button(file_buttons, text="Add folder", style="Secondary.TButton", command=self._add_folder).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(
            file_buttons,
            text="Remove selected",
            style="Secondary.TButton",
            command=self._remove_selected,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(file_buttons, text="Clear", style="Danger.TButton", command=self._clear_files).pack(
            side="right"
        )

        settings_border, settings_card = self._card(outer)
        settings_border.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        settings_card.columnconfigure(0, weight=1)

        ttk.Label(settings_card, text="Conversion settings", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            settings_card,
            text="Choose the destination and how large structures should be exported.",
            style="CardText.TLabel",
            wraplength=350,
        ).grid(row=1, column=0, sticky="w", pady=(4, 16))

        ttk.Label(settings_card, text="Output directory", style="CardValue.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 6)
        )
        output_row = ttk.Frame(settings_card, style="Card.TFrame")
        output_row.grid(row=3, column=0, sticky="ew")
        output_row.columnconfigure(0, weight=1)
        ttk.Entry(output_row, textvariable=self.output_var, style="Modern.TEntry").grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(output_row, text="Browse", style="Secondary.TButton", command=self._choose_output).grid(
            row=0, column=1, padx=(8, 0)
        )
        ttk.Button(output_row, text="Open", style="Secondary.TButton", command=self._open_output).grid(
            row=0, column=2, padx=(8, 0)
        )

        size_row = ttk.Frame(settings_card, style="Card.TFrame")
        size_row.grid(row=4, column=0, sticky="ew", pady=(16, 4))
        size_row.columnconfigure(0, weight=1)
        ttk.Label(size_row, text="Maximum size per axis", style="CardValue.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Spinbox(
            size_row,
            from_=1,
            to=512,
            textvariable=self.max_size_var,
            width=7,
            justify="center",
            style="Modern.TSpinbox",
        ).grid(row=0, column=1, sticky="e")
        ttk.Label(
            settings_card,
            text="48 is recommended for vanilla structure blocks.",
            style="CardText.TLabel",
        ).grid(row=5, column=0, sticky="w", pady=(0, 10))

        checks = ttk.Frame(settings_card, style="Card.TFrame")
        checks.grid(row=6, column=0, sticky="ew")
        ttk.Checkbutton(
            checks,
            text="Automatically split oversized structures",
            variable=self.split_var,
            style="Modern.TCheckbutton",
        ).pack(anchor="w", fill="x")
        ttk.Checkbutton(
            checks,
            text="Include air blocks (preserves cleared areas)",
            variable=self.air_var,
            style="Modern.TCheckbutton",
        ).pack(anchor="w", fill="x")
        ttk.Checkbutton(
            checks,
            text="Preserve imported folder structure",
            variable=self.preserve_tree_var,
            style="Modern.TCheckbutton",
        ).pack(anchor="w", fill="x")
        ttk.Checkbutton(
            checks,
            text="Overwrite existing output files",
            variable=self.overwrite_var,
            style="Modern.TCheckbutton",
        ).pack(anchor="w", fill="x")

        action_area = ttk.Frame(settings_card, style="Card.TFrame")
        action_area.grid(row=7, column=0, sticky="ew", pady=(14, 0))
        action_area.columnconfigure(0, weight=1)
        self.convert_button = ttk.Button(
            action_area,
            text="Start conversion",
            style="Primary.TButton",
            command=self._start_conversion,
        )
        self.convert_button.grid(row=0, column=0, sticky="ew")

        activity_border, activity_card = self._card(outer)
        activity_border.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        activity_card.columnconfigure(0, weight=1)

        activity_header = ttk.Frame(activity_card, style="Card.TFrame")
        activity_header.grid(row=0, column=0, sticky="ew")
        activity_header.columnconfigure(0, weight=1)
        ttk.Label(activity_header, text="Activity", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(activity_header, textvariable=self.progress_text_var, style="CardText.TLabel").grid(
            row=0, column=1, sticky="e"
        )

        self.progress = ttk.Progressbar(
            activity_card,
            mode="determinate",
            style="Modern.Horizontal.TProgressbar",
        )
        self.progress.grid(row=1, column=0, sticky="ew", pady=(10, 6))
        ttk.Label(activity_card, textvariable=self.status_var, style="Status.TLabel").grid(
            row=2, column=0, sticky="w"
        )

        log_container = tk.Frame(
            activity_card,
            background=COLORS["field"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        log_container.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        log_container.columnconfigure(0, weight=1)
        log_container.rowconfigure(0, weight=1)
        self.log = tk.Text(
            log_container,
            height=5,
            state="disabled",
            wrap="word",
            background=COLORS["field"],
            foreground=COLORS["muted"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["selection"],
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=8,
            font=("Consolas" if sys.platform.startswith("win") else "DejaVu Sans Mono", 9),
        )
        self.log.grid(row=0, column=0, sticky="ew")
        log_scroll = ttk.Scrollbar(log_container, orient="vertical", command=self.log.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=log_scroll.set)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-o>", lambda _event: self._add_files())
        self.root.bind("<Control-Shift-O>", lambda _event: self._add_folder())
        self.root.bind("<Delete>", lambda _event: self._remove_selected())
        self.root.bind("<F5>", lambda _event: self._start_conversion())

    def _update_file_count(self) -> None:
        count = self.file_list.size()
        self.file_count_var.set(f"{count} file" if count == 1 else f"{count} files")

    def _add_path(self, path: Path, source_root: Path | None = None) -> None:
        if path.suffix.lower() not in {".schem", ".litematic"}:
            return
        resolved_path = path.expanduser().resolve()
        if not resolved_path.is_file():
            return
        resolved = str(resolved_path)
        existing = set(self.file_list.get(0, tk.END))
        if resolved not in existing:
            self.file_list.insert(tk.END, resolved)

        # A later folder import replaces an earlier root assignment so the
        # behavior stays predictable when a file is first added individually.
        if source_root is not None:
            self.source_roots[resolved] = source_root.expanduser().resolve()
        else:
            self.source_roots.setdefault(resolved, None)
        self._update_file_count()

    def _add_directory(self, folder: Path) -> None:
        root = folder.expanduser().resolve()
        for path in sorted(root.rglob("*")):
            self._add_path(path, source_root=root)

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select Minecraft schematics",
            filetypes=[
                ("Minecraft schematics", "*.schem *.litematic"),
                ("Sponge schematic", "*.schem"),
                ("Litematica schematic", "*.litematic"),
                ("All files", "*.*"),
            ],
        )
        for path in paths:
            self._add_path(Path(path))

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select a folder to scan recursively")
        if folder:
            self._add_directory(Path(folder))

    def _remove_selected(self) -> None:
        for index in reversed(self.file_list.curselection()):
            value = self.file_list.get(index)
            self.source_roots.pop(value, None)
            self.file_list.delete(index)
        self._update_file_count()

    def _clear_files(self) -> None:
        self.file_list.delete(0, tk.END)
        self.source_roots.clear()
        self._update_file_count()

    def _choose_output(self) -> None:
        initial = self.output_var.get().strip() or str(Path.home())
        folder = filedialog.askdirectory(title="Select the output directory", initialdir=initial)
        if folder:
            self.output_var.set(folder)

    def _open_output(self) -> None:
        raw_output = self.output_var.get().strip()
        if not raw_output:
            messagebox.showwarning("Missing output directory", "Choose an output directory first.")
            return
        output = Path(raw_output).expanduser()
        try:
            output.mkdir(parents=True, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(output)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(output)])
            else:
                subprocess.Popen(["xdg-open", str(output)])
        except (OSError, subprocess.SubprocessError) as exc:
            messagebox.showerror("Unable to open folder", str(exc))

    def _on_drop(self, event) -> None:
        for raw in self.root.tk.splitlist(event.data):
            path = Path(raw)
            if path.is_dir():
                self._add_directory(path)
            else:
                self._add_path(path)

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def _start_conversion(self) -> None:
        if self.running:
            return

        values = list(self.file_list.get(0, tk.END))
        jobs = [(Path(value), self.source_roots.get(value)) for value in values]
        if not jobs:
            messagebox.showwarning(
                "No input files",
                "Add at least one .schem or .litematic file before starting.",
            )
            return

        raw_output = self.output_var.get().strip()
        if not raw_output:
            messagebox.showerror("Invalid output directory", "Choose an output directory.")
            return
        output = Path(raw_output).expanduser()

        try:
            max_size = int(self.max_size_var.get())
            if max_size < 1:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror("Invalid option", "Maximum size must be a positive integer.")
            return

        self.running = True
        self.convert_button.configure(state="disabled", text="Converting…")
        self.progress.configure(maximum=len(jobs), value=0)
        self.progress_text_var.set(f"0 / {len(jobs)}")
        self.status_var.set("Preparing conversion…")
        self._append_log("")
        self._append_log(f"Starting batch: {len(jobs)} input file(s)")

        options = {
            "split_large": bool(self.split_var.get()),
            "include_air": bool(self.air_var.get()),
            "overwrite": bool(self.overwrite_var.get()),
            "preserve_tree": bool(self.preserve_tree_var.get()),
        }
        thread = threading.Thread(
            target=self._worker,
            args=(jobs, output, max_size, options),
            daemon=True,
        )
        thread.start()

    def _worker(
        self,
        jobs: list[tuple[Path, Path | None]],
        output: Path,
        max_size: int,
        options: dict[str, bool],
    ) -> None:
        success = 0
        errors: list[str] = []
        total = len(jobs)
        for index, (path, source_root) in enumerate(jobs, start=1):
            self.messages.put(("status", f"Converting {path.name} ({index}/{total})"))
            try:
                effective_root = source_root if options["preserve_tree"] else None
                results = convert_file(
                    path,
                    output,
                    max_size=max_size,
                    split_large=options["split_large"],
                    include_air=options["include_air"],
                    overwrite=options["overwrite"],
                    source_root=effective_root,
                    progress=lambda msg: self.messages.put(("log", msg)),
                )
                success += 1
                destination = results[0].parent
                self.messages.put(
                    ("log", f"✓ {path.name}: created {len(results)} file(s) in {destination}")
                )
            except (ConversionError, OSError, ValueError) as exc:
                message = f"✗ {path.name}: {exc}"
                errors.append(message)
                self.messages.put(("log", message))
            self.messages.put(("progress", (index, total)))
        self.messages.put(("done", (success, len(errors), output)))

    def _poll_messages(self) -> None:
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "log":
                    self._append_log(str(payload))
                elif kind == "status":
                    self.status_var.set(str(payload))
                elif kind == "progress":
                    index, total = payload
                    self.progress.configure(value=int(index))
                    self.progress_text_var.set(f"{index} / {total}")
                elif kind == "done":
                    success, errors, output = payload
                    self.running = False
                    self.convert_button.configure(state="normal", text="Start conversion")
                    self.status_var.set(
                        f"Finished — {success} succeeded, {errors} failed"
                    )
                    self._append_log(
                        f"Batch finished: {success} succeeded, {errors} failed. Output: {output}"
                    )
                    if errors:
                        messagebox.showwarning(
                            "Conversion finished with errors",
                            f"{success} file(s) converted successfully.\n"
                            f"{errors} file(s) failed.\n\n"
                            "See the activity log for details.",
                        )
                    else:
                        messagebox.showinfo(
                            "Conversion complete",
                            f"{success} file(s) converted successfully.\n\nOutput: {output}",
                        )
        except queue.Empty:
            pass
        self.root.after(100, self._poll_messages)


def run_gui() -> None:
    if TkinterDnD is not None:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    ConverterApp(root)
    root.mainloop()
