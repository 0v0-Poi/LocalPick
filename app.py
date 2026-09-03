"""Local Pick — tkinter GUI for random local folder/file picking."""

from __future__ import annotations

import copy
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import core

APP_TITLE = "Local Pick"
WIN_SIZE = "640x520"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WIN_SIZE)
        self.minsize(560, 460)
        try:
            self.option_add("*Font", "{Microsoft YaHei UI} 10")
        except tk.TclError:
            pass

        try:
            self.cfg = core.load_config()
        except core.PickError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            self.cfg = core.default_config()

        self.category: dict | None = None
        self.current_path: Path | None = None
        self._settings_index = 0

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.container = ttk.Frame(self, padding=16)
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(0, weight=1)

        self.frames: dict[str, ttk.Frame] = {}
        for name, factory in (
            ("home", self._build_home),
            ("result", self._build_result),
            ("settings", self._build_settings),
        ):
            frame = ttk.Frame(self.container)
            frame.grid(row=0, column=0, sticky="nsew")
            factory(frame)
            self.frames[name] = frame

        self.show("home")

    def show(self, name: str) -> None:
        if name == "home":
            self.refresh_home()
        self.frames[name].tkraise()

    def _handle(self, exc: Exception) -> None:
        messagebox.showerror(APP_TITLE, str(exc))

    # --- home ---
    def _build_home(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text="本地随机抽取", font=("Microsoft YaHei UI", 16, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(frame, text="自己选一个大类，或让程序抽。抽中文件夹可以再往里抽一层。").grid(
            row=1, column=0, sticky="w", pady=(0, 12)
        )
        self.last_box = ttk.LabelFrame(frame, text="继续上次", padding=8)
        self.last_box.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.last_box.columnconfigure(0, weight=1)
        self.pick_box = ttk.LabelFrame(frame, text="自己选大类", padding=8)
        self.pick_box.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.pick_box.columnconfigure(0, weight=1)
        ttk.Button(frame, text="程序随机抽一个大类", command=self.on_random_category).grid(
            row=4, column=0, sticky="ew", pady=(0, 8), ipady=4
        )
        ttk.Button(frame, text="设置路径和大类", command=self.open_settings).grid(
            row=5, column=0, sticky="ew", ipady=2
        )

    def refresh_home(self) -> None:
        for child in self.last_box.winfo_children():
            child.destroy()
        for child in self.pick_box.winfo_children():
            child.destroy()

        last_row = 0
        for category in self.cfg["categories"]:
            path = core.last_path(self.cfg, category["id"])
            if path is None:
                continue
            text = f"继续上次「{category['name']}」\n{path}"
            ttk.Button(
                self.last_box,
                text=text,
                command=lambda c=category, p=path: self.show_existing(c, p),
            ).grid(row=last_row, column=0, sticky="ew", pady=2)
            last_row += 1
        if last_row == 0:
            ttk.Label(self.last_box, text="还没有记录。抽中并打开之后会出现在这里。").grid(
                row=0, column=0, sticky="w"
            )

        for i, category in enumerate(self.cfg["categories"]):
            ttk.Button(
                self.pick_box,
                text=category["name"],
                command=lambda c=category: self.pick_from_category(c),
            ).grid(row=i, column=0, sticky="ew", pady=2, ipady=2)

    def on_random_category(self) -> None:
        try:
            category = core.pick_category(self.cfg)
        except core.PickError as exc:
            self._handle(exc)
            return
        self.pick_from_category(category)

    def pick_from_category(self, category: dict) -> None:
        try:
            root = core.category_root(category)
            picked = core.pick_one(core.list_candidates(self.cfg, category, root))
        except core.PickError as exc:
            self._handle(exc)
            return
        self.show_result(category, picked)

    def show_existing(self, category: dict, path: Path) -> None:
        self.show_result(category, path)

    def show_result(self, category: dict, path: Path) -> None:
        self.category = category
        self.current_path = Path(path)
        self.refresh_result()
        self.show("result")

    # --- result ---
    def _build_result(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(3, weight=1)
        self.result_title = ttk.Label(frame, text="", font=("Microsoft YaHei UI", 14, "bold"))
        self.result_title.grid(row=0, column=0, sticky="w")
        self.result_kind = ttk.Label(frame, text="")
        self.result_kind.grid(row=1, column=0, sticky="w", pady=(4, 8))
        self.result_path = ttk.Label(frame, text="", wraplength=580, justify="left")
        self.result_path.grid(row=2, column=0, sticky="ew")
        self.result_actions = ttk.Frame(frame)
        self.result_actions.grid(row=4, column=0, sticky="ew", pady=(16, 0))
        self.result_actions.columnconfigure(0, weight=1)
        ttk.Button(frame, text="从头再来", command=lambda: self.show("home")).grid(
            row=5, column=0, sticky="ew", pady=(12, 0)
        )

    def refresh_result(self) -> None:
        assert self.category is not None and self.current_path is not None
        path = self.current_path
        is_dir = path.is_dir()
        kind = "文件夹" if is_dir else "文件"
        self.result_title.configure(text=f"抽中 · {self.category['name']}")
        self.result_kind.configure(text=kind)
        self.result_path.configure(text=str(path))
        for child in self.result_actions.winfo_children():
            child.destroy()
        row = 0

        def add_btn(text: str, cmd) -> None:
            nonlocal row
            ttk.Button(self.result_actions, text=text, command=cmd).grid(
                row=row, column=0, sticky="ew", pady=3, ipady=3
            )
            row += 1

        if is_dir:
            add_btn("再抽一层", self.on_deeper)
            add_btn("打开文件夹", self.on_open_folder)
            add_btn("在资源管理器中显示", self.on_reveal)
            return

        if self.category.get("open_mode") == "folder_only":
            add_btn("打开所在文件夹", self.on_open_folder)
            add_btn("在资源管理器中显示", self.on_reveal)
            return

        add_btn("直接打开", self.on_open_file)
        add_btn("在资源管理器中显示", self.on_reveal)

    def on_deeper(self) -> None:
        if self.category is None or self.current_path is None:
            return
        try:
            picked = core.pick_one(
                core.list_candidates(self.cfg, self.category, self.current_path)
            )
        except core.PickError as exc:
            self._handle(exc)
            return
        self.show_result(self.category, picked)

    def _remember(self) -> None:
        if self.category is None or self.current_path is None:
            return
        try:
            core.record_last(self.cfg, self.category["id"], self.current_path)
        except core.PickError as exc:
            self._handle(exc)

    def on_open_file(self) -> None:
        if self.current_path is None:
            return
        try:
            core.open_file(self.current_path)
            self._remember()
        except (core.PickError, OSError) as exc:
            self._handle(exc)

    def on_open_folder(self) -> None:
        if self.current_path is None:
            return
        try:
            core.open_folder(self.current_path)
            self._remember()
        except (core.PickError, OSError) as exc:
            self._handle(exc)

    def on_reveal(self) -> None:
        if self.current_path is None:
            return
        try:
            core.reveal_in_explorer(self.current_path)
            self._remember()
        except (core.PickError, OSError) as exc:
            self._handle(exc)

    # --- settings ---
    def _build_settings(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="设置", font=("Microsoft YaHei UI", 16, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        self.cat_list = tk.Listbox(frame, height=12, exportselection=False)
        self.cat_list.grid(row=1, column=0, sticky="nsw", padx=(0, 12))
        self.cat_list.bind("<<ListboxSelect>>", self.on_select_category)

        form = ttk.Frame(frame)
        form.grid(row=1, column=1, sticky="nsew")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="名称").grid(row=0, column=0, sticky="w", pady=4)
        self.var_name = tk.StringVar()
        ttk.Entry(form, textvariable=self.var_name).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="路径").grid(row=1, column=0, sticky="w", pady=4)
        path_row = ttk.Frame(form)
        path_row.grid(row=1, column=1, sticky="ew", pady=4)
        path_row.columnconfigure(0, weight=1)
        self.var_path = tk.StringVar()
        ttk.Entry(path_row, textvariable=self.var_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(path_row, text="浏览…", command=self.browse_path, width=8).grid(
            row=0, column=1, padx=(6, 0)
        )

        ttk.Label(form, text="打开方式").grid(row=2, column=0, sticky="w", pady=4)
        self.var_mode = tk.StringVar(value="file")
        mode = ttk.Combobox(
            form,
            textvariable=self.var_mode,
            state="readonly",
            values=("file", "folder_only"),
        )
        mode.grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(
            form,
            text="file = 文件可直接打开；folder_only = 只开文件夹（游戏用）",
            wraplength=360,
        ).grid(row=3, column=1, sticky="w")

        ttk.Label(form, text="扩展名").grid(row=4, column=0, sticky="nw", pady=4)
        self.var_exts = tk.StringVar()
        ttk.Entry(form, textvariable=self.var_exts).grid(row=4, column=1, sticky="ew", pady=4)
        ttk.Label(form, text="逗号分隔，例如 .mp4, .mkv, .exe", wraplength=360).grid(
            row=5, column=1, sticky="w"
        )

        btns = ttk.Frame(frame)
        btns.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(btns, text="新增大类", command=self.add_category_row).pack(side="left")
        ttk.Button(btns, text="删除当前大类", command=self.delete_category_row).pack(
            side="left", padx=8
        )
        ttk.Button(btns, text="保存", command=self.save_settings).pack(side="right")
        ttk.Button(btns, text="返回", command=self.cancel_settings).pack(side="right", padx=8)

        self.var_name.trace_add("write", lambda *_: self._write_form_to_draft())
        self.var_path.trace_add("write", lambda *_: self._write_form_to_draft())
        self.var_mode.trace_add("write", lambda *_: self._write_form_to_draft())
        self.var_exts.trace_add("write", lambda *_: self._write_form_to_draft())
        self._syncing_form = False
        self.draft_cfg = copy.deepcopy(self.cfg)

    def open_settings(self) -> None:
        self.draft_cfg = copy.deepcopy(self.cfg)
        self.reload_category_list(0)
        self.show("settings")

    def cancel_settings(self) -> None:
        self.show("home")

    def reload_category_list(self, select: int = 0) -> None:
        self.cat_list.delete(0, tk.END)
        for category in self.draft_cfg["categories"]:
            self.cat_list.insert(tk.END, category["name"])
        if not self.draft_cfg["categories"]:
            return
        select = max(0, min(select, len(self.draft_cfg["categories"]) - 1))
        self.cat_list.selection_clear(0, tk.END)
        self.cat_list.selection_set(select)
        self.cat_list.activate(select)
        self._settings_index = select
        self._load_form(select)

    def on_select_category(self, _event=None) -> None:
        sel = self.cat_list.curselection()
        if not sel:
            return
        self._settings_index = int(sel[0])
        self._load_form(self._settings_index)

    def _load_form(self, index: int) -> None:
        category = self.draft_cfg["categories"][index]
        self._syncing_form = True
        self.var_name.set(category["name"])
        self.var_path.set(category["path"])
        self.var_mode.set(category.get("open_mode") or "file")
        self.var_exts.set(", ".join(category.get("extensions") or []))
        self._syncing_form = False

    def _write_form_to_draft(self) -> None:
        if self._syncing_form:
            return
        cats = self.draft_cfg["categories"]
        if not cats:
            return
        index = min(self._settings_index, len(cats) - 1)
        category = cats[index]
        category["name"] = self.var_name.get().strip() or "未命名"
        category["path"] = self.var_path.get().strip()
        mode = self.var_mode.get().strip()
        category["open_mode"] = mode if mode in ("file", "folder_only") else "file"
        category["extensions"] = [
            core._norm_ext(part) for part in self.var_exts.get().split(",") if core._norm_ext(part)
        ]
        current = self.cat_list.get(index) if index < self.cat_list.size() else ""
        if current != category["name"]:
            self.cat_list.delete(index)
            self.cat_list.insert(index, category["name"])
            self.cat_list.selection_set(index)

    def browse_path(self) -> None:
        initial = self.var_path.get().strip() or None
        chosen = filedialog.askdirectory(initialdir=initial or None)
        if chosen:
            self.var_path.set(chosen)

    def add_category_row(self) -> None:
        self._write_form_to_draft()
        core.add_category(self.draft_cfg, core.new_category())
        self.reload_category_list(len(self.draft_cfg["categories"]) - 1)

    def delete_category_row(self) -> None:
        self._write_form_to_draft()
        if not self.draft_cfg["categories"]:
            return
        cid = self.draft_cfg["categories"][self._settings_index]["id"]
        try:
            core.delete_category(self.draft_cfg, cid)
        except core.PickError as exc:
            self._handle(exc)
            return
        self.reload_category_list(min(self._settings_index, len(self.draft_cfg["categories"]) - 1))

    def save_settings(self) -> None:
        self._write_form_to_draft()
        try:
            core.save_config(self.draft_cfg)
            self.cfg = core.load_config()
        except core.PickError as exc:
            self._handle(exc)
            return
        messagebox.showinfo(APP_TITLE, "已保存。")
        self.show("home")


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
