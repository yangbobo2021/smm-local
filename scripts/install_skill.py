"""Install one portable skill in Claude Code and Codex user skill roots."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=Path.home(), help="Home directory (use a temporary path for validation)")
    parser.add_argument("--update", action="store_true", help="Update an existing smm-search skill")
    args = parser.parse_args()
    for name in ("smm-search", "smm-source-adapter"):
        install_skill(name, args.home, args.update)


def install_skill(name: str, home: Path, update: bool) -> None:
    source = Path(__file__).resolve().parents[1] / "skills" / name
    for target in [home / ".codex/skills" / name, home / ".claude/skills" / name]:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            existing = target / "SKILL.md"
            if not existing.is_file() or f"name: {name}" not in existing.read_text(encoding="utf-8").splitlines()[:5]:
                raise SystemExit(f"已有不同技能，未覆盖：{target}")
            if existing.read_bytes() == (source / "SKILL.md").read_bytes():
                print(target, "(已安装)")
            elif update:
                shutil.copy2(source / "SKILL.md", existing)
                print(target, "(已更新)")
            else:
                raise SystemExit(f"已有不同版本；如需更新请加 --update：{target}")
        else:
            target.mkdir()
            shutil.copy2(source / "SKILL.md", target)
            print(target)
        if (source / "scripts").is_dir():
            shutil.copytree(source / "scripts", target / "scripts", dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
        if (source / "protocol.md").is_file():
            shutil.copy2(source / "protocol.md", target / "protocol.md")


if __name__ == "__main__":
    main()
