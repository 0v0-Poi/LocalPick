"""Local Pick core: config, candidate listing, random pick, open/reveal."""

from __future__ import annotations

import json
import os
import random
import stat
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

CONFIG_NAME = "config.json"

DEFAULT_VIDEO_EXTS = [".mp4", ".mkv", ".avi", ".wmv", ".webm", ".ts", ".mov"]
DEFAULT_SKIP_DIRS = ["DwnlData", "$RECYCLE.BIN", "System Volume Information"]
DEFAULT_SKIP_EXTS = [
    ".torrent",
    ".nfo",
    ".txt",
    ".srt",
    ".url",
    ".ini",
    ".log",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
]


class PickError(Exception):
    """User-facing pick/config error."""


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def config_path() -> Path:
    return app_dir() / CONFIG_NAME


def default_config() -> dict[str, Any]:
    categories = [
        {
            "id": "mmd",
            "name": "MMD",
            "path": "",
            "open_mode": "file",
            "extensions": list(DEFAULT_VIDEO_EXTS),
        },
        {
            "id": "video",
            "name": "视频",
            "path": "",
            "open_mode": "file",
            "extensions": list(DEFAULT_VIDEO_EXTS),
        },
        {
            "id": "game",
            "name": "游戏",
            "path": "",
            "open_mode": "folder_only",
            "extensions": [".exe"],
        },
    ]
    return {
        "categories": categories,
        "last": {c["id"]: None for c in categories},
        "skip_dir_names": list(DEFAULT_SKIP_DIRS),
        "skip_extensions": list(DEFAULT_SKIP_EXTS),
    }


def _norm_ext(ext: str) -> str:
    ext = ext.strip().lower()
    if not ext:
        return ""
    return ext if ext.startswith(".") else f".{ext}"


def normalize_config(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise PickError("配置文件格式无效")
    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        raise PickError("配置里没有大类")
    last = data.get("last")
    if not isinstance(last, dict):
        last = {}
    cleaned = []
    for raw in categories:
        if not isinstance(raw, dict):
            continue
        cid = str(raw.get("id") or uuid.uuid4())
        name = str(raw.get("name") or "未命名").strip() or "未命名"
        path = str(raw.get("path") or "").strip()
        open_mode = str(raw.get("open_mode") or "file").strip()
        if open_mode not in ("file", "folder_only"):
            open_mode = "file"
        exts = raw.get("extensions") or []
        if not isinstance(exts, list):
            exts = []
        extensions = [_norm_ext(e) for e in exts if _norm_ext(e)]
        cleaned.append(
            {
                "id": cid,
                "name": name,
                "path": path,
                "open_mode": open_mode,
                "extensions": extensions,
            }
        )
        last.setdefault(cid, last.get(cid))
    if not cleaned:
        raise PickError("配置里没有有效大类")
    skip_dirs = data.get("skip_dir_names") or list(DEFAULT_SKIP_DIRS)
    if not isinstance(skip_dirs, list):
        skip_dirs = list(DEFAULT_SKIP_DIRS)
    skip_exts = data.get("skip_extensions") or list(DEFAULT_SKIP_EXTS)
    if not isinstance(skip_exts, list):
        skip_exts = list(DEFAULT_SKIP_EXTS)
    keep_ids = {c["id"] for c in cleaned}
    last = {k: v for k, v in last.items() if k in keep_ids}
    for c in cleaned:
        last.setdefault(c["id"], None)
    return {
        "categories": cleaned,
        "last": last,
        "skip_dir_names": [str(x) for x in skip_dirs],
        "skip_extensions": [_norm_ext(str(x)) for x in skip_exts if _norm_ext(str(x))],
    }


def load_config(path: Path | None = None) -> dict[str, Any]:
    path = path or config_path()
    if not path.is_file():
        cfg = default_config()
        save_config(cfg, path)
        return cfg
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PickError(f"无法读取配置：{exc}") from exc
    cfg = normalize_config(data)
    return cfg


def save_config(cfg: dict[str, Any], path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(normalize_config(cfg), ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def category_by_id(cfg: dict[str, Any], category_id: str) -> dict[str, Any]:
    for item in cfg["categories"]:
        if item["id"] == category_id:
            return item
    raise PickError("找不到这个大类")


def is_hidden(path: Path) -> bool:
    if path.name.startswith("."):
        return True
    try:
        attrs = path.stat().st_file_attributes  # type: ignore[attr-defined]
        return bool(attrs & stat.FILE_ATTRIBUTE_HIDDEN)
    except (AttributeError, OSError):
        return False


def category_root(category: dict[str, Any]) -> Path:
    raw = (category.get("path") or "").strip()
    if not raw:
        raise PickError(f"「{category.get('name', '')}」还没有填写文件夹路径")
    root = Path(raw)
    if not root.is_dir():
        raise PickError(f"「{category.get('name', '')}」的路径不存在或不是文件夹：{raw}")
    return root


def list_candidates(cfg: dict[str, Any], category: dict[str, Any], folder: Path) -> list[Path]:
    folder = Path(folder)
    if not folder.is_dir():
        raise PickError(f"不是文件夹：{folder}")
    skip_dirs = {name.lower() for name in cfg.get("skip_dir_names", [])}
    allowed = {ext.lower() for ext in category.get("extensions", [])}
    items: list[Path] = []
    try:
        children = list(folder.iterdir())
    except OSError as exc:
        raise PickError(f"无法读取文件夹：{exc}") from exc
    for child in children:
        try:
            if is_hidden(child):
                continue
            if child.is_dir():
                if child.name.lower() in skip_dirs:
                    continue
                items.append(child)
                continue
            if child.is_file() and child.suffix.lower() in allowed:
                items.append(child)
        except OSError:
            continue
    return items


def pick_one(candidates: list[Path]) -> Path:
    if not candidates:
        raise PickError("这一层没有可抽的文件或文件夹")
    return random.choice(candidates)


def usable_categories(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    usable = []
    for category in cfg["categories"]:
        try:
            root = category_root(category)
            if list_candidates(cfg, category, root):
                usable.append(category)
        except PickError:
            continue
    return usable


def pick_category(cfg: dict[str, Any]) -> dict[str, Any]:
    usable = usable_categories(cfg)
    if not usable:
        raise PickError("没有可抽的大类：请先在设置里填好存在且非空的文件夹路径")
    return random.choice(usable)


def record_last(cfg: dict[str, Any], category_id: str, path: Path, save_to: Path | None = None) -> None:
    cfg.setdefault("last", {})
    cfg["last"][category_id] = str(Path(path))
    save_config(cfg, save_to)


def last_path(cfg: dict[str, Any], category_id: str) -> Path | None:
    raw = (cfg.get("last") or {}).get(category_id)
    if not raw:
        return None
    path = Path(str(raw))
    if path.exists():
        return path
    return None


def new_category(
    name: str = "新分类",
    path: str = "",
    open_mode: str = "file",
    extensions: list[str] | None = None,
) -> dict[str, Any]:
    if open_mode not in ("file", "folder_only"):
        open_mode = "file"
    return {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "path": path,
        "open_mode": open_mode,
        "extensions": list(extensions or DEFAULT_VIDEO_EXTS),
    }


def add_category(cfg: dict[str, Any], category: dict[str, Any] | None = None) -> dict[str, Any]:
    category = category or new_category()
    cfg["categories"].append(category)
    cfg.setdefault("last", {})[category["id"]] = None
    return category


def delete_category(cfg: dict[str, Any], category_id: str) -> None:
    cfg["categories"] = [c for c in cfg["categories"] if c["id"] != category_id]
    if not cfg["categories"]:
        raise PickError("至少保留一个大类")
    (cfg.get("last") or {}).pop(category_id, None)


def open_file(path: Path) -> None:
    path = Path(path)
    if not path.is_file():
        raise PickError(f"不是文件：{path}")
    os.startfile(path)  # type: ignore[attr-defined]


def open_folder(path: Path) -> None:
    path = Path(path)
    target = path if path.is_dir() else path.parent
    if not target.is_dir():
        raise PickError(f"找不到文件夹：{target}")
    os.startfile(target)  # type: ignore[attr-defined]


def reveal_in_explorer(path: Path) -> None:
    path = Path(path).resolve()
    if not path.exists():
        raise PickError(f"路径不存在：{path}")
    if os.name == "nt":
        subprocess.run(["explorer", "/select,", str(path)], check=False)
        return
    parent = path if path.is_dir() else path.parent
    subprocess.run(["xdg-open", str(parent)], check=False)
