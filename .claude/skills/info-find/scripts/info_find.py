#!/usr/bin/env python3
"""Static information extractor for local files using bundled regex rules."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        try:
            return ast.literal_eval(value)
        except Exception:
            return value[1:-1]
    return value


def load_rules(rule_path: Path) -> list[dict[str, Any]]:
    text = read_text(rule_path)
    rules: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "regex_rules:":
            continue
        if stripped.startswith("- "):
            if current:
                rules.append(current)
            current = {}
            remainder = stripped[2:].strip()
            if remainder and ":" in remainder:
                key, value = remainder.split(":", 1)
                current[key.strip()] = parse_scalar(value)
            continue
        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = parse_scalar(value)

    if current:
        rules.append(current)

    enabled_rules = [rule for rule in rules if rule.get("enabled", True)]
    for rule in enabled_rules:
        if "name" not in rule or "pattern" not in rule:
            raise ValueError(f"Invalid rule in {rule_path}: {rule}")
    return enabled_rules


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def iter_files(paths: list[str], max_size: int) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        if re.match(r"^https?://", raw, re.I):
            print(
                f"[skip] URL 不会被脚本自动访问，请先手动保存为本地文件：{raw}",
                file=sys.stderr,
            )
            continue
        path = Path(raw)
        if path.is_file():
            if should_read(path, max_size):
                files.append(path)
            continue
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and should_read(child, max_size):
                    files.append(child)
            continue
        print(f"[skip] 路径不存在：{raw}", file=sys.stderr)
    return sorted(set(files))


def should_read(path: Path, max_size: int) -> bool:
    try:
        stat = path.stat()
        if stat.st_size > max_size:
            return False
        with path.open("rb") as handle:
            sample = handle.read(4096)
        return b"\x00" not in sample
    except OSError:
        return False


def clean_match(value: str, category: str) -> str:
    value = value.strip().strip("\"'`")
    if category == "sensitive":
        return value[:80]
    return value[:500]


def extract(files: list[Path], rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for file_path in files:
        try:
            text = read_text(file_path)
        except OSError as exc:
            print(f"[skip] 无法读取：{file_path} ({exc})", file=sys.stderr)
            continue

        for rule in rules:
            flags = re.MULTILINE
            pattern = str(rule["pattern"])
            group = int(rule.get("match_group", 0))
            try:
                compiled = re.compile(pattern, flags)
            except re.error as exc:
                print(f"[skip] 规则无法编译：{rule.get('name')} ({exc})", file=sys.stderr)
                continue

            for match in compiled.finditer(text):
                try:
                    value = match.group(group)
                except IndexError:
                    value = match.group(0)
                if value is None:
                    continue
                category = str(rule.get("category", "unknown"))
                cleaned = clean_match(str(value), category)
                key = (str(rule.get("name")), cleaned)
                if key in seen:
                    continue
                seen.add(key)

                item = {
                    "rule": rule.get("name"),
                    "match": cleaned,
                }
                results.append(item)
    return results


def group_results(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in results:
        rule = str(item["rule"])
        grouped.setdefault(rule, {"count": "0", "data": []})
        grouped[rule]["data"].append(item["match"])
    for value in grouped.values():
        value["count"] = str(len(value["data"]))
    return grouped


def to_markdown(grouped: dict[str, dict[str, Any]]) -> str:
    rows: list[str] = []
    for rule, result in grouped.items():
        rows.append(f"{rule} ({result['count']})")
        rows.extend(str(item) for item in result["data"])
        rows.append("")
    return "\n".join(rows).rstrip() + "\n"


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    default_rules = script_dir.parent / "rules" / "rule.yml"

    parser = argparse.ArgumentParser(description="对本地文件或目录执行正则信息提取")
    parser.add_argument("paths", nargs="+", help="本地文件或目录。不会自动访问 URL。")
    parser.add_argument("--rules", default=str(default_rules), help="规则文件路径")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--format", choices=("json", "markdown"), default="json", help="输出格式")
    parser.add_argument("--max-size-mb", type=int, default=5, help="单文件最大读取大小")
    args = parser.parse_args()

    rule_path = Path(args.rules)
    max_size = args.max_size_mb * 1024 * 1024
    rules = load_rules(rule_path)
    files = iter_files(args.paths, max_size)
    results = extract(files, rules)
    grouped = group_results(results)

    if args.format == "markdown":
        output = to_markdown(grouped)
    else:
        output = json.dumps(grouped, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
