import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import core


def _touch(path: Path, name: str) -> Path:
    file_path = path / name
    file_path.write_bytes(b"x")
    return file_path


class CoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg_path = self.root / "config.json"
        self.video_root = self.root / "videos"
        self.video_root.mkdir()
        self.game_root = self.root / "games"
        self.game_root.mkdir()
        _touch(self.video_root, "a.mp4")
        _touch(self.video_root, "skip.torrent")
        _touch(self.video_root, "cover.jpg")
        _touch(self.video_root, "note.txt")
        (self.video_root / "actor").mkdir()
        (self.video_root / "DwnlData").mkdir()
        _touch(self.video_root / "actor", "b.mp4")
        _touch(self.video_root / "actor", "b.nfo")
        (self.game_root / "rpg").mkdir()
        _touch(self.game_root / "rpg", "Game.exe")
        _touch(self.game_root / "rpg", "readme.txt")
        self.cfg = {
            "categories": [
                {
                    "id": "video",
                    "name": "视频",
                    "path": str(self.video_root),
                    "open_mode": "file",
                    "extensions": list(core.DEFAULT_VIDEO_EXTS),
                },
                {
                    "id": "game",
                    "name": "游戏",
                    "path": str(self.game_root),
                    "open_mode": "folder_only",
                    "extensions": [".exe"],
                },
            ],
            "last": {"video": None, "game": None},
            "skip_dir_names": list(core.DEFAULT_SKIP_DIRS),
            "skip_extensions": list(core.DEFAULT_SKIP_EXTS),
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_list_candidates_filters_junk_and_dwnldata(self) -> None:
        video = core.category_by_id(self.cfg, "video")
        names = {p.name for p in core.list_candidates(self.cfg, video, self.video_root)}
        self.assertIn("a.mp4", names)
        self.assertIn("actor", names)
        self.assertNotIn("skip.torrent", names)
        self.assertNotIn("cover.jpg", names)
        self.assertNotIn("note.txt", names)
        self.assertNotIn("DwnlData", names)

    def test_nested_folder_only_keeps_media(self) -> None:
        video = core.category_by_id(self.cfg, "video")
        names = {p.name for p in core.list_candidates(self.cfg, video, self.video_root / "actor")}
        self.assertEqual(names, {"b.mp4"})

    def test_game_root_is_folders_only(self) -> None:
        game = core.category_by_id(self.cfg, "game")
        items = core.list_candidates(self.cfg, game, self.game_root)
        self.assertEqual([p.name for p in items], ["rpg"])

    def test_game_inner_picks_exe_not_readme(self) -> None:
        game = core.category_by_id(self.cfg, "game")
        names = {p.name for p in core.list_candidates(self.cfg, game, self.game_root / "rpg")}
        self.assertEqual(names, {"Game.exe"})

    def test_extension_case_insensitive(self) -> None:
        _touch(self.video_root, "C.MP4")
        video = core.category_by_id(self.cfg, "video")
        names = {p.name for p in core.list_candidates(self.cfg, video, self.video_root)}
        self.assertIn("C.MP4", names)

    def test_hidden_file_skipped(self) -> None:
        hidden = _touch(self.video_root, "secret.mp4")
        hidden.stat().st_file_attributes  # ensure path exists
        hidden.write_bytes(b"x")
        try:
            hidden.stat()
            os_stat = hidden.stat()
            if hasattr(os_stat, "st_file_attributes"):
                import ctypes

                ctypes.windll.kernel32.SetFileAttributesW(str(hidden), 2)
        except Exception:
            hidden.rename(self.video_root / ".secret.mp4")
            hidden = self.video_root / ".secret.mp4"
        video = core.category_by_id(self.cfg, "video")
        names = {p.name for p in core.list_candidates(self.cfg, video, self.video_root)}
        self.assertNotIn(hidden.name, names)

    def test_pick_one_empty_raises(self) -> None:
        with self.assertRaises(core.PickError):
            core.pick_one([])

    def test_pick_one_single(self) -> None:
        path = self.video_root / "a.mp4"
        self.assertEqual(core.pick_one([path]), path)

    def test_pick_category_skips_empty_and_missing(self) -> None:
        empty = self.root / "empty"
        empty.mkdir()
        self.cfg["categories"].append(
            {
                "id": "missing",
                "name": "空",
                "path": str(empty),
                "open_mode": "file",
                "extensions": [".mp4"],
            }
        )
        self.cfg["categories"].append(
            {
                "id": "gone",
                "name": "没了",
                "path": str(self.root / "nope"),
                "open_mode": "file",
                "extensions": [".mp4"],
            }
        )
        picked_ids = {core.pick_category(self.cfg)["id"] for _ in range(20)}
        self.assertTrue(picked_ids <= {"video", "game"})
        self.assertIn("video", picked_ids)

    def test_load_creates_default_when_missing(self) -> None:
        cfg = core.load_config(self.cfg_path)
        self.assertTrue(self.cfg_path.is_file())
        self.assertEqual(len(cfg["categories"]), 3)
        self.assertEqual({c["id"] for c in cfg["categories"]}, {"mmd", "video", "game"})

    def test_default_config_has_no_personal_paths(self) -> None:
        dumped = json.dumps(core.default_config(), ensure_ascii=False)
        self.assertNotRegex(dumped, r"[A-Za-z]:\\\\")
        for category in core.default_config()["categories"]:
            self.assertEqual(category["path"], "")

    def test_record_last_roundtrip(self) -> None:
        core.save_config(self.cfg, self.cfg_path)
        core.record_last(self.cfg, "video", self.video_root / "a.mp4", self.cfg_path)
        loaded = core.load_config(self.cfg_path)
        self.assertEqual(Path(loaded["last"]["video"]), self.video_root / "a.mp4")
        self.assertEqual(core.last_path(loaded, "video"), self.video_root / "a.mp4")

    def test_last_path_missing_returns_none(self) -> None:
        self.cfg["last"]["video"] = str(self.root / "deleted.mp4")
        self.assertIsNone(core.last_path(self.cfg, "video"))

    def test_add_and_delete_category(self) -> None:
        added = core.add_category(self.cfg, core.new_category("图包", str(self.root), "file", [".jpg"]))
        self.assertEqual(added["name"], "图包")
        self.assertIn(added["id"], self.cfg["last"])
        core.delete_category(self.cfg, added["id"])
        self.assertNotIn(added["id"], {c["id"] for c in self.cfg["categories"]})
        with self.assertRaises(core.PickError):
            core.delete_category(self.cfg, "video")
            core.delete_category(self.cfg, "game")

    def test_normalize_drops_unknown_last_keys(self) -> None:
        self.cfg["last"]["ghost"] = "x"
        cleaned = core.normalize_config(self.cfg)
        self.assertNotIn("ghost", cleaned["last"])

    def test_image_pack_allowlist_not_blocked_by_skip_exts(self) -> None:
        pack = self.root / "pics"
        pack.mkdir()
        _touch(pack, "a.jpg")
        _touch(pack, "b.png")
        cat = {
            "id": "pics",
            "name": "图包",
            "path": str(pack),
            "open_mode": "file",
            "extensions": [".jpg", ".png"],
        }
        names = {p.name for p in core.list_candidates(self.cfg, cat, pack)}
        self.assertEqual(names, {"a.jpg", "b.png"})


if __name__ == "__main__":
    unittest.main()
