#!/usr/bin/env python3
"""Decrypt and unpack Windows WeChat Mini Program wxapkg files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
AES_IV = b"the iv: 16 bytes"
AES_SALT = b"saltiest"
DEFAULT_XOR_KEY = 0x66
DEFAULT_WUWXAPKG_DIR = Path(r"D:\Tools\MiniSpy-last\WorkDir\wuWxapkg-2")
TAB_BAR_UNSUPPORTED_KEYS = {
    "fontSize",
    "iconData",
    "selectedIconData",
}
RUNTIME_RESIDUE_MARKERS = (
    "$gwx",
    "$gwn",
    "__wxAppCode__",
    "__WXML_GLOBAL__",
    "generateFuncReady",
)
COMPILED_ARTIFACT_NAMES = (
    "app-config.json",
    "app-service.js",
    "app-wxss.js",
    "common.js",
    "page-frame.js",
    "page-frame.html",
)
NON_PAGE_DIR_NAMES = {
    "_compiled",
    "assets",
    "asset",
    "common",
    "component",
    "components",
    "image",
    "images",
    "miniprogram_npm",
    "npm",
    "static",
    "style",
    "styles",
    "utils",
}


@dataclass
class PackageResult:
    source: str
    decrypted: str
    output: str
    label: str
    kind: str
    file_count: int
    package_root: str = ""
    merge_prefix: str = ""
    restore_dir: str = ""
    error: str = ""


@dataclass
class RunResult:
    appid: str
    applet_root: str
    matched_dir: str
    output_root: str
    wxapkg_count: int = 0
    packages: list[PackageResult] = field(default_factory=list)
    merged_files: int = 0
    conflicts: int = 0
    restored_files: int = 0
    restore_engine: str = "python-basic"
    failed: int = 0


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def is_wxapkg(data: bytes) -> bool:
    return len(data) >= 14 and data[0] == 0xBE and data[13] == 0xED


def looks_encrypted(data: bytes) -> bool:
    return data.startswith(b"V1MMWX") or not is_wxapkg(data)


def pkcs7_unpad(data: bytes) -> bytes:
    if not data:
        raise ValueError("empty AES output")
    pad = data[-1]
    if pad < 1 or pad > 16:
        raise ValueError("invalid AES padding")
    if data[-pad:] != bytes([pad]) * pad:
        raise ValueError("invalid AES padding bytes")
    return data[:-pad]


def decrypt_with_pycryptodome(block: bytes, key: bytes) -> bytes | None:
    try:
        from Crypto.Cipher import AES  # type: ignore
    except Exception:
        return None
    cipher = AES.new(key, AES.MODE_CBC, AES_IV)
    return pkcs7_unpad(cipher.decrypt(block))


SBOX = [
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
]

INV_SBOX = [
    0x52, 0x09, 0x6A, 0xD5, 0x30, 0x36, 0xA5, 0x38, 0xBF, 0x40, 0xA3, 0x9E, 0x81, 0xF3, 0xD7, 0xFB,
    0x7C, 0xE3, 0x39, 0x82, 0x9B, 0x2F, 0xFF, 0x87, 0x34, 0x8E, 0x43, 0x44, 0xC4, 0xDE, 0xE9, 0xCB,
    0x54, 0x7B, 0x94, 0x32, 0xA6, 0xC2, 0x23, 0x3D, 0xEE, 0x4C, 0x95, 0x0B, 0x42, 0xFA, 0xC3, 0x4E,
    0x08, 0x2E, 0xA1, 0x66, 0x28, 0xD9, 0x24, 0xB2, 0x76, 0x5B, 0xA2, 0x49, 0x6D, 0x8B, 0xD1, 0x25,
    0x72, 0xF8, 0xF6, 0x64, 0x86, 0x68, 0x98, 0x16, 0xD4, 0xA4, 0x5C, 0xCC, 0x5D, 0x65, 0xB6, 0x92,
    0x6C, 0x70, 0x48, 0x50, 0xFD, 0xED, 0xB9, 0xDA, 0x5E, 0x15, 0x46, 0x57, 0xA7, 0x8D, 0x9D, 0x84,
    0x90, 0xD8, 0xAB, 0x00, 0x8C, 0xBC, 0xD3, 0x0A, 0xF7, 0xE4, 0x58, 0x05, 0xB8, 0xB3, 0x45, 0x06,
    0xD0, 0x2C, 0x1E, 0x8F, 0xCA, 0x3F, 0x0F, 0x02, 0xC1, 0xAF, 0xBD, 0x03, 0x01, 0x13, 0x8A, 0x6B,
    0x3A, 0x91, 0x11, 0x41, 0x4F, 0x67, 0xDC, 0xEA, 0x97, 0xF2, 0xCF, 0xCE, 0xF0, 0xB4, 0xE6, 0x73,
    0x96, 0xAC, 0x74, 0x22, 0xE7, 0xAD, 0x35, 0x85, 0xE2, 0xF9, 0x37, 0xE8, 0x1C, 0x75, 0xDF, 0x6E,
    0x47, 0xF1, 0x1A, 0x71, 0x1D, 0x29, 0xC5, 0x89, 0x6F, 0xB7, 0x62, 0x0E, 0xAA, 0x18, 0xBE, 0x1B,
    0xFC, 0x56, 0x3E, 0x4B, 0xC6, 0xD2, 0x79, 0x20, 0x9A, 0xDB, 0xC0, 0xFE, 0x78, 0xCD, 0x5A, 0xF4,
    0x1F, 0xDD, 0xA8, 0x33, 0x88, 0x07, 0xC7, 0x31, 0xB1, 0x12, 0x10, 0x59, 0x27, 0x80, 0xEC, 0x5F,
    0x60, 0x51, 0x7F, 0xA9, 0x19, 0xB5, 0x4A, 0x0D, 0x2D, 0xE5, 0x7A, 0x9F, 0x93, 0xC9, 0x9C, 0xEF,
    0xA0, 0xE0, 0x3B, 0x4D, 0xAE, 0x2A, 0xF5, 0xB0, 0xC8, 0xEB, 0xBB, 0x3C, 0x83, 0x53, 0x99, 0x61,
    0x17, 0x2B, 0x04, 0x7E, 0xBA, 0x77, 0xD6, 0x26, 0xE1, 0x69, 0x14, 0x63, 0x55, 0x21, 0x0C, 0x7D,
]

RCON = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


def xtime(value: int) -> int:
    value <<= 1
    if value & 0x100:
        value ^= 0x11B
    return value & 0xFF


def gf_mul(a: int, b: int) -> int:
    result = 0
    while b:
        if b & 1:
            result ^= a
        a = xtime(a)
        b >>= 1
    return result


def expand_key(key: bytes) -> list[list[int]]:
    nk = len(key) // 4
    nb = 4
    nr = nk + 6
    words = [list(key[i : i + 4]) for i in range(0, len(key), 4)]
    for i in range(nk, nb * (nr + 1)):
        temp = words[i - 1].copy()
        if i % nk == 0:
            temp = temp[1:] + temp[:1]
            temp = [SBOX[b] for b in temp]
            temp[0] ^= RCON[i // nk]
        elif nk > 6 and i % nk == 4:
            temp = [SBOX[b] for b in temp]
        words.append([a ^ b for a, b in zip(words[i - nk], temp)])
    return [sum(words[i : i + 4], []) for i in range(0, len(words), 4)]


def add_round_key(state: list[int], round_key: list[int]) -> None:
    for i in range(16):
        state[i] ^= round_key[i]


def inv_sub_bytes(state: list[int]) -> None:
    for i, value in enumerate(state):
        state[i] = INV_SBOX[value]


def inv_shift_rows(state: list[int]) -> None:
    rows = [[state[r + 4 * c] for c in range(4)] for r in range(4)]
    for r in range(1, 4):
        rows[r] = rows[r][-r:] + rows[r][:-r]
    for r in range(4):
        for c in range(4):
            state[r + 4 * c] = rows[r][c]


def inv_mix_columns(state: list[int]) -> None:
    for c in range(4):
        col = [state[r + 4 * c] for r in range(4)]
        state[0 + 4 * c] = gf_mul(col[0], 14) ^ gf_mul(col[1], 11) ^ gf_mul(col[2], 13) ^ gf_mul(col[3], 9)
        state[1 + 4 * c] = gf_mul(col[0], 9) ^ gf_mul(col[1], 14) ^ gf_mul(col[2], 11) ^ gf_mul(col[3], 13)
        state[2 + 4 * c] = gf_mul(col[0], 13) ^ gf_mul(col[1], 9) ^ gf_mul(col[2], 14) ^ gf_mul(col[3], 11)
        state[3 + 4 * c] = gf_mul(col[0], 11) ^ gf_mul(col[1], 13) ^ gf_mul(col[2], 9) ^ gf_mul(col[3], 14)


def aes_decrypt_block(block: bytes, round_keys: list[list[int]]) -> bytes:
    state = list(block)
    nr = len(round_keys) - 1
    add_round_key(state, round_keys[nr])
    for round_idx in range(nr - 1, 0, -1):
        inv_shift_rows(state)
        inv_sub_bytes(state)
        add_round_key(state, round_keys[round_idx])
        inv_mix_columns(state)
    inv_shift_rows(state)
    inv_sub_bytes(state)
    add_round_key(state, round_keys[0])
    return bytes(state)


def aes_cbc_decrypt_builtin(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    if len(ciphertext) % 16 != 0:
        raise ValueError("AES ciphertext length is not multiple of 16")
    round_keys = expand_key(key)
    previous = iv
    output = bytearray()
    for offset in range(0, len(ciphertext), 16):
        block = ciphertext[offset : offset + 16]
        decrypted = aes_decrypt_block(block, round_keys)
        output.extend(a ^ b for a, b in zip(decrypted, previous))
        previous = block
    return pkcs7_unpad(bytes(output))


def aes_cbc_decrypt(ciphertext: bytes, key: bytes) -> bytes:
    result = decrypt_with_pycryptodome(ciphertext, key)
    if result is not None:
        return result
    return aes_cbc_decrypt_builtin(ciphertext, key, AES_IV)


def decrypt_wxapkg(data: bytes, appid: str) -> bytes:
    if is_wxapkg(data):
        return data
    if len(data) <= 1024:
        raise ValueError("encrypted package is too small")

    key = hashlib.pbkdf2_hmac("sha1", appid.encode("utf-8"), AES_SALT, 1000, 32)
    offset = 6 if data.startswith(b"V1MMWX") else 0
    encrypted_head = data[offset : offset + 1024]
    xor_body = data[offset + 1024 :]
    head = aes_cbc_decrypt(encrypted_head, key)
    xor_key = ord(appid[-2]) if len(appid) >= 2 else DEFAULT_XOR_KEY
    body = bytes(byte ^ xor_key for byte in xor_body)
    decoded = head + body
    if not is_wxapkg(decoded):
        raise ValueError("decryption completed but wxapkg magic was not found")
    return decoded


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value.strip("._") or "package"


def unique_dir(base: Path, name: str) -> Path:
    candidate = base / safe_name(name)
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        next_candidate = base / f"{safe_name(name)}_{index}"
        if not next_candidate.exists():
            return next_candidate
        index += 1


def sanitize_member_path(raw_name: str) -> Path:
    name = raw_name.replace("\\", "/").lstrip("/")
    parts = []
    for part in name.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            raise ValueError(f"unsafe path in package: {raw_name}")
        parts.append(part)
    if not parts:
        raise ValueError(f"empty path in package: {raw_name}")
    return Path(*parts)


def unpack_wxapkg(data: bytes, output_dir: Path) -> list[str]:
    if not is_wxapkg(data):
        raise ValueError("invalid wxapkg magic")
    if len(data) < 18:
        raise ValueError("invalid wxapkg header")

    marker1 = data[0]
    _unknown = struct.unpack(">I", data[1:5])[0]
    index_len = struct.unpack(">I", data[5:9])[0]
    body_len = struct.unpack(">I", data[9:13])[0]
    marker2 = data[13]
    info_count = struct.unpack(">I", data[14:18])[0]
    if marker1 != 0xBE or marker2 != 0xED:
        raise ValueError("invalid wxapkg header marker")
    if 14 + index_len + body_len > len(data):
        raise ValueError("wxapkg length mismatch")

    offset = 18
    extracted: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for _ in range(info_count):
        if offset + 4 > len(data):
            raise ValueError("unexpected end while reading filename length")
        name_len = struct.unpack(">I", data[offset : offset + 4])[0]
        offset += 4
        raw_name = data[offset : offset + name_len].decode("utf-8", errors="replace")
        offset += name_len
        if offset + 8 > len(data):
            raise ValueError("unexpected end while reading file index")
        file_offset, file_size = struct.unpack(">II", data[offset : offset + 8])
        offset += 8
        member_path = sanitize_member_path(raw_name)
        content = data[file_offset : file_offset + file_size]
        if len(content) != file_size:
            raise ValueError(f"file content out of range: {raw_name}")
        target = output_dir / member_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        extracted.append(member_path.as_posix())

    return extracted


def find_app_dir(root: Path, appid: str) -> Path:
    if not root.exists():
        raise FileNotFoundError(f"WECHAT_APPLET_ROOT not found: {root}")
    matches: list[Path] = []
    for child in root.rglob("*"):
        if child.is_dir() and appid.lower() in child.name.lower():
            if any(grandchild.is_file() and grandchild.suffix.lower() == ".wxapkg" for grandchild in child.rglob("*")):
                matches.append(child)
    if not matches:
        raise FileNotFoundError(f"appid directory not found under WECHAT_APPLET_ROOT: {appid}")
    matches.sort(key=lambda path: (len(path.parts), str(path).lower()))
    return matches[0]


def collect_wxapkg_files(app_dir: Path) -> list[Path]:
    files = [path for path in app_dir.rglob("*") if path.is_file() and path.suffix.lower() == ".wxapkg"]
    return sorted(files, key=package_sort_key)


def package_sort_key(path: Path) -> tuple[int, str]:
    name = path.name.lower()
    rank = 0 if "__app__" in name or name == "app.wxapkg" else 1
    return rank, str(path).lower()


def select_package_dir(app_dir: Path) -> Path:
    direct_files = [path for path in app_dir.glob("*.wxapkg") if path.is_file()]
    if direct_files:
        return app_dir

    candidates = [
        child
        for child in app_dir.iterdir()
        if child.is_dir() and any(path.is_file() and path.suffix.lower() == ".wxapkg" for path in child.rglob("*"))
    ]
    if not candidates:
        return app_dir

    numeric_candidates = [path for path in candidates if path.name.isdigit()]
    if numeric_candidates:
        return max(numeric_candidates, key=lambda path: int(path.name))
    return max(candidates, key=lambda path: path.stat().st_mtime)


def classify_package(output_dir: Path, files: list[str]) -> str:
    lower = {name.lower() for name in files}
    if "app.json" in lower or "app-config.json" in lower or "app-service.js" in lower:
        return "main"
    if any(name.startswith("app-service") for name in lower):
        return "main"
    return "sub"


def read_json_file(path: Path) -> Any | None:
    if not path.exists():
        return None
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
        except json.JSONDecodeError:
            return None
    return None


def load_subpackage_roots(main_dir: Path) -> list[str]:
    roots: list[str] = []
    for config_name in ("app.json", "app-config.json"):
        app_json = read_json_file(main_dir / config_name)
        if not isinstance(app_json, dict):
            continue
        subpackages = app_json.get("subPackages") or app_json.get("subpackages") or []
        if isinstance(subpackages, list):
            for item in subpackages:
                if isinstance(item, dict) and isinstance(item.get("root"), str):
                    roots.append(item["root"].strip("/\\"))
    return list(dict.fromkeys(root for root in roots if root))


def detect_package_root(files: list[str], roots: list[str]) -> str:
    normalized = [name.replace("\\", "/").lstrip("/") for name in files]
    for root in roots:
        prefix = root.strip("/\\") + "/"
        if any(name.startswith(prefix) for name in normalized):
            return root.strip("/\\")
    return ""


def infer_package_root_from_source(package: PackageResult, roots: list[str]) -> str:
    haystack = f"{package.source} {package.label}".replace("\\", "/").lower()
    candidates: list[str] = []
    for root in roots:
        normalized = root.strip("/\\").lower()
        if not normalized:
            continue
        variants = {normalized, safe_name(normalized).lower(), normalized.replace("/", "_")}
        if any(variant and variant in haystack for variant in variants):
            candidates.append(root.strip("/\\"))
    return candidates[0] if len(set(candidates)) == 1 else ""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unlink_with_retry(path: Path, retries: int = 10) -> None:
    last_error: OSError | None = None
    for attempt in range(retries):
        try:
            path.unlink()
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.15 * (attempt + 1))
    if last_error:
        raise last_error


def move_with_retry(source: Path, target: Path, retries: int = 10) -> None:
    last_error: OSError | None = None
    for attempt in range(retries):
        try:
            shutil.move(str(source), str(target))
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.15 * (attempt + 1))
    if last_error:
        raise last_error


def remove_tree_with_retry(path: Path, retries: int = 10) -> None:
    last_error: OSError | None = None
    for attempt in range(retries):
        try:
            shutil.rmtree(path)
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.15 * (attempt + 1))
    if last_error:
        raise last_error


def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def copy_tree_with_conflicts(source: Path, destination: Path, conflicts_dir: Path, prefix: str = "") -> tuple[int, int]:
    merged = 0
    conflicts = 0
    prefix_path = sanitize_member_path(prefix) if prefix else Path()
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        relative = prefix_path / path.relative_to(source)
        target = destination / relative
        if target.exists():
            if file_sha256(path) == file_sha256(target):
                continue
            conflict_target = conflicts_dir / relative
            conflict_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, conflict_target)
            conflicts += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        merged += 1
    return merged, conflicts


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def unique_list(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def warning_invalid_keys(value: Any) -> set[str]:
    if not isinstance(value, dict):
        return set()
    warning = value.get("__warning__")
    if not isinstance(warning, str):
        return set()
    return set(re.findall(r'\["([^"]+)"\]', warning))


def warning_invalid_child_keys(value: Any) -> dict[str, set[str]]:
    if not isinstance(value, dict):
        return {}
    warning = value.get("__warning__")
    if not isinstance(warning, str):
        return {}
    result: dict[str, set[str]] = {}
    for parent, key in re.findall(r'([A-Za-z0-9_$.-]+)\["([^"]+)"\]', warning):
        result.setdefault(parent, set()).add(key)
    return result


def clean_config_dict(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    invalid = warning_invalid_keys(value)
    cleaned: dict[str, Any] = {}
    for key, item in value.items():
        if key.startswith("__") or key in invalid:
            continue
        if isinstance(item, dict):
            cleaned[key] = clean_config_dict(item)
        elif isinstance(item, list):
            cleaned[key] = [clean_config_dict(child) for child in item]
        else:
            cleaned[key] = item
    return cleaned


def clean_warning_dict(value: Any) -> tuple[Any, int]:
    if isinstance(value, dict):
        invalid = warning_invalid_keys(value)
        invalid_child_keys = warning_invalid_child_keys(value)
        changed = 0
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if key == "__warning__" or key in invalid:
                changed += 1
                continue
            cleaned_item, item_changed = clean_warning_dict(item)
            if key in invalid_child_keys and isinstance(cleaned_item, dict):
                for child_key in invalid_child_keys[key]:
                    if child_key in cleaned_item:
                        cleaned_item.pop(child_key, None)
                        item_changed += 1
            cleaned[key] = cleaned_item
            changed += item_changed
        return cleaned, changed
    if isinstance(value, list):
        changed = 0
        cleaned_items = []
        for item in value:
            cleaned_item, item_changed = clean_warning_dict(item)
            cleaned_items.append(cleaned_item)
            changed += item_changed
        return cleaned_items, changed
    return value, 0


def sanitize_json_warning_files(merged_dir: Path) -> int:
    changed_files = 0
    for path in merged_dir.rglob("*.json"):
        if "_compiled" in path.parts:
            continue
        value = read_json_file(path)
        if value is None:
            continue
        cleaned, changed = clean_warning_dict(value)
        if changed:
            json_dump(path, cleaned)
            changed_files += 1
    return changed_files


def convert_simple_object_attr(match: re.Match[str]) -> str:
    attr = match.group("attr")
    key = match.group("key")
    value = match.group("value")
    return f'{attr}="{key}:{value}"'


def sanitize_wxml_content(content: str) -> tuple[str, int]:
    pattern = re.compile(
        r'(?P<attr>[A-Za-z_:][-A-Za-z0-9_:.]*)="\{\{\s*(?P<key>[A-Za-z_-][A-Za-z0-9_-]*)\s*:\s*\'(?P<value>[^\'{}]*)\'\s*\}\}"'
    )
    return pattern.subn(convert_simple_object_attr, content)


def sanitize_wxml_files(merged_dir: Path) -> dict[str, Any]:
    changed_files = 0
    replacements = 0
    files: list[str] = []
    for path in merged_dir.rglob("*.wxml"):
        if "_compiled" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        cleaned, changed = sanitize_wxml_content(content)
        if not changed:
            continue
        path.write_text(cleaned, encoding="utf-8")
        changed_files += 1
        replacements += changed
        files.append(path.relative_to(merged_dir).as_posix())
    return {
        "changed_files": changed_files,
        "replacements": replacements,
        "files": files[:100],
    }


def normalize_page_path(value: str) -> str:
    normalized = value.replace("\\", "/").lstrip("/")
    if normalized.endswith(".html"):
        normalized = normalized[:-5]
    for suffix in (".wxml", ".js", ".json", ".wxss"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
    return normalized


def clean_window_config(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return value
    return clean_config_dict(value)


def normalize_tab_bar(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = clean_window_config(value)
    for key in TAB_BAR_UNSUPPORTED_KEYS:
        normalized.pop(key, None)
    items = normalized.get("list")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                for key in TAB_BAR_UNSUPPORTED_KEYS:
                    item.pop(key, None)
                if isinstance(item.get("pagePath"), str):
                    item["pagePath"] = normalize_page_path(item["pagePath"])
    return normalized


def build_app_json(app_config: dict[str, Any]) -> dict[str, Any]:
    app_json: dict[str, Any] = {}
    pages = app_config.get("pages")
    if isinstance(pages, list):
        app_json["pages"] = [
            page
            for page in (normalize_page_path(str(item)) for item in pages)
            if page and not page.startswith("__plugin__/")
        ]

    entry_page = app_config.get("entryPagePath")
    if isinstance(entry_page, str):
        normalized_entry = normalize_page_path(entry_page)
        if normalized_entry and normalized_entry not in app_json.get("pages", []):
            app_json.setdefault("pages", []).insert(0, normalized_entry)

    global_config = app_config.get("global")
    if isinstance(global_config, dict):
        for key, value in global_config.items():
            if key.startswith("__"):
                continue
            app_json[key] = clean_window_config(value)

    for key in ("tabBar", "networkTimeout", "debug", "permission", "plugins", "requiredPrivateInfos", "usingComponents"):
        value = app_config.get(key)
        if value is not None:
            app_json[key] = normalize_tab_bar(value) if key == "tabBar" else clean_window_config(value)

    subpackages = app_config.get("subPackages") or app_config.get("subpackages")
    if isinstance(subpackages, list):
        restored_subpackages = []
        page_list = app_json.get("pages", [])
        for item in subpackages:
            if not isinstance(item, dict) or not isinstance(item.get("root"), str):
                continue
            root = item["root"].strip("/\\")
            if not root:
                continue
            restored = {key: clean_window_config(value) for key, value in item.items() if not key.startswith("__") and key != "plugins"}
            restored["root"] = root
            prefix = root.rstrip("/") + "/"
            pages_in_root = []
            for page in page_list:
                if page.startswith(prefix):
                    pages_in_root.append(page[len(prefix) :])
            if pages_in_root:
                restored["pages"] = pages_in_root
            restored_subpackages.append(restored)
        if restored_subpackages:
            app_json["subPackages"] = restored_subpackages
            app_json["pages"] = [
                page
                for page in app_json.get("pages", [])
                if not any(page.startswith(item["root"].rstrip("/") + "/") for item in restored_subpackages)
            ]

    return app_json


def page_json_from_config(app_config: dict[str, Any], page: str) -> dict[str, Any]:
    page_map = app_config.get("page")
    if not isinstance(page_map, dict):
        return {}
    candidates = [page, page + ".html", page + ".wxml"]
    for candidate in candidates:
        item = page_map.get(candidate)
        if isinstance(item, dict):
            window = item.get("window")
            if isinstance(window, dict):
                return clean_window_config(window)
            return clean_window_config(item)
    return {}


def copy_html_to_wxml(html_path: Path) -> Path:
    wxml_path = html_path.with_suffix(".wxml")
    if not wxml_path.exists():
        content = html_path.read_text(encoding="utf-8", errors="replace").replace("\x00", "")
        if is_runtime_html(content):
            content = "<view></view>\n"
        wxml_path.write_text(content, encoding="utf-8")
    return wxml_path


def is_runtime_html(content: str) -> bool:
    return any(marker in content for marker in RUNTIME_RESIDUE_MARKERS)


def is_compiled_wxml_runtime_js(content: str) -> bool:
    head = content[:20000]
    if "__wxAppCode__" in head and ("__WXML_GLOBAL__" in head or "global.__wcc_version__" in head):
        return True
    if re.search(r"\$gwx(?:_[A-Za-z0-9_]+)?\s*=\s*function", head):
        return True
    if re.search(r"function\s+\$gwx(?:_[A-Za-z0-9_]+)?\s*\(", head):
        return True
    return False


def is_runtime_residue(path: Path) -> bool:
    if path.suffix.lower() not in {".js", ".wxml", ".html"}:
        return False
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if path.suffix.lower() == ".html":
        return is_runtime_html(content)
    if path.suffix.lower() == ".wxml":
        return is_runtime_html(content)
    if path.suffix.lower() == ".js":
        if not is_compiled_wxml_runtime_js(content):
            return False
        head = content[:20000]
        if path.name == "app.js":
            return True
        return "Page(" not in head and "Component(" not in head and "App(" not in head
    return False


def quarantine_file(path: Path, merged_dir: Path, reason: str) -> Path:
    relative = path.relative_to(merged_dir)
    target = merged_dir / "_compiled" / reason / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if file_sha256(path) == file_sha256(target):
            unlink_with_retry(path)
            return target
        target = target.with_name(f"{target.stem}_{int(time.time())}{target.suffix}")
    move_with_retry(path, target)
    return target


def candidate_page_files(merged_dir: Path) -> list[str]:
    pages: list[str] = []
    for path in merged_dir.rglob("*.js"):
        relative = path.relative_to(merged_dir)
        if len(relative.parts) < 2:
            continue
        parts = {part.lower() for part in relative.parts}
        if parts & NON_PAGE_DIR_NAMES:
            continue
        if relative.parts[0].lower() in {"__plugin__", "plugin"}:
            continue
        if path.name in COMPILED_ARTIFACT_NAMES:
            continue
        stem = path.with_suffix("")
        page = stem.relative_to(merged_dir).as_posix()
        if "/" not in page:
            continue
        if any(stem.with_suffix(ext).exists() for ext in (".wxml", ".json")):
            pages.append(page)
    return sorted(unique_list(pages))


def registered_pages(app_json: dict[str, Any]) -> set[str]:
    pages = {
        normalize_page_path(page)
        for page in app_json.get("pages", [])
        if isinstance(page, str)
    }
    subpackages = app_json.get("subPackages") or app_json.get("subpackages") or []
    if isinstance(subpackages, list):
        for subpackage in subpackages:
            if not isinstance(subpackage, dict) or not isinstance(subpackage.get("root"), str):
                continue
            root = subpackage["root"].strip("/\\")
            for page in subpackage.get("pages", []):
                if isinstance(page, str):
                    pages.add(normalize_page_path(f"{root}/{page}"))
    return pages


def add_unregistered_existing_pages(app_json: dict[str, Any], pages: list[str]) -> int:
    subpackages = app_json.get("subPackages")
    if not isinstance(subpackages, list):
        subpackages = []
    existing = registered_pages(app_json)
    added = 0
    for page in pages:
        if page in existing or page.startswith("__plugin__/"):
            continue
        matched_subpackage = None
        for subpackage in subpackages:
            if not isinstance(subpackage, dict) or not isinstance(subpackage.get("root"), str):
                continue
            root = subpackage["root"].strip("/\\").rstrip("/")
            if root and page.startswith(root + "/"):
                matched_subpackage = subpackage
                rel_page = page[len(root) + 1 :]
                page_list = matched_subpackage.setdefault("pages", [])
                if isinstance(page_list, list) and rel_page not in page_list:
                    page_list.append(rel_page)
                    added += 1
                break
        if matched_subpackage is None:
            app_json.setdefault("pages", []).append(page)
            added += 1
        existing.add(page)
    return added


def repair_runtime_residue(merged_dir: Path) -> dict[str, Any]:
    quarantined: list[str] = []
    skipped: list[dict[str, str]] = []
    replaced_wxml = 0
    replaced_js = 0
    replaced_app = 0
    for path in list(merged_dir.rglob("*")):
        if not path.is_file() or "_compiled" in path.parts:
            continue
        if path.name in COMPILED_ARTIFACT_NAMES:
            continue
        if not is_runtime_residue(path):
            continue
        if path.suffix.lower() == ".wxml":
            try:
                quarantine_file(path, merged_dir, "runtime-residue")
                path.write_text("<view></view>\n", encoding="utf-8")
                replaced_wxml += 1
                quarantined.append(path.relative_to(merged_dir).as_posix())
            except OSError as exc:
                skipped.append({
                    "file": path.relative_to(merged_dir).as_posix(),
                    "error": str(exc),
                })
            continue
        try:
            quarantined_path = quarantine_file(path, merged_dir, "runtime-residue")
            quarantined.append(quarantined_path.relative_to(merged_dir).as_posix())
            if path.suffix.lower() == ".js" and path.name == "app.js":
                path.write_text("App({})\n", encoding="utf-8")
                replaced_app += 1
            elif path.suffix.lower() == ".js" and is_page_like_script(path, merged_dir):
                path.write_text(default_page_script(path), encoding="utf-8")
                replaced_js += 1
        except OSError as exc:
            skipped.append({
                "file": path.relative_to(merged_dir).as_posix(),
                "error": str(exc),
            })
    return {
        "quarantined": quarantined,
        "skipped": skipped,
        "replaced_wxml": replaced_wxml,
        "replaced_js": replaced_js,
        "replaced_app": replaced_app,
    }


def is_page_like_script(path: Path, merged_dir: Path) -> bool:
    relative = path.relative_to(merged_dir)
    parts = {part.lower() for part in relative.parts}
    if parts & NON_PAGE_DIR_NAMES:
        return False
    return (
        relative.parts[0].lower() == "pages"
        or path.with_suffix(".wxml").exists()
        or path.with_suffix(".json").exists()
    )


def default_page_script(path: Path) -> str:
    page_json = read_json_file(path.with_suffix(".json"))
    if isinstance(page_json, dict) and page_json.get("component") is True:
        return "Component({})\n"
    return "Page({})\n"


def ensure_app_files_basic(merged_dir: Path) -> int:
    created = 0
    app_js = merged_dir / "app.js"
    if not app_js.exists():
        app_js.write_text("App({})\n", encoding="utf-8")
        created += 1
    app_wxss = merged_dir / "app.wxss"
    if not app_wxss.exists():
        app_wxss.write_text("", encoding="utf-8")
        created += 1
    return created


def move_compiled_artifacts(merged_dir: Path) -> dict[str, Any]:
    moved = 0
    skipped: list[dict[str, str]] = []
    for path in list(merged_dir.rglob("*")):
        if not path.is_file() or "_compiled" in path.parts:
            continue
        if path.name not in COMPILED_ARTIFACT_NAMES:
            continue
        try:
            quarantine_file(path, merged_dir, "compiled-artifacts")
            moved += 1
        except OSError as exc:
            skipped.append({
                "file": path.relative_to(merged_dir).as_posix(),
                "error": str(exc),
            })
    return {"moved": moved, "skipped": skipped}


def validate_restored_project(merged_dir: Path) -> dict[str, Any]:
    app_json = read_json_file(merged_dir / "app.json")
    issues: list[dict[str, Any]] = []
    if not isinstance(app_json, dict):
        return {"issues": [{"type": "missing_app_json", "message": "app.json 不存在或不是合法 JSON"}]}

    for page in sorted(registered_pages(app_json)):
        missing_exts = [
            ext
            for ext in (".js", ".wxml", ".json", ".wxss")
            if not (merged_dir / Path(page)).with_suffix(ext).exists()
        ]
        if missing_exts:
            issues.append({"type": "missing_page_files", "page": page, "missing": missing_exts})

    runtime_files = []
    for path in merged_dir.rglob("*"):
        if path.is_file() and "_compiled" not in path.parts and is_runtime_residue(path):
            runtime_files.append(path.relative_to(merged_dir).as_posix())
    if runtime_files:
        issues.append({"type": "runtime_residue", "files": runtime_files[:100], "count": len(runtime_files)})

    return {"issues": issues}


def postprocess_restored_project(merged_dir: Path) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "created": 0,
        "registered_existing_pages": 0,
        "sanitized_json_files": 0,
        "sanitized_wxml": {},
        "moved_compiled_artifacts": 0,
        "skipped_compiled_artifacts": [],
        "runtime_residue": {},
        "validation": {},
    }
    created = normalize_app_json_after_restore(merged_dir)
    created += ensure_app_files_basic(merged_dir)
    stats["created"] = created

    app_json_path = merged_dir / "app.json"
    app_json = read_json_file(app_json_path)
    if isinstance(app_json, dict):
        added = add_unregistered_existing_pages(app_json, candidate_page_files(merged_dir))
        if added:
            for page in app_json.get("pages", []):
                if isinstance(page, str):
                    created += ensure_page_files_basic(merged_dir, page)
            for subpackage in app_json.get("subPackages", []):
                if not isinstance(subpackage, dict) or not isinstance(subpackage.get("root"), str):
                    continue
                root = subpackage["root"].strip("/\\")
                for page in subpackage.get("pages", []):
                    if isinstance(page, str):
                        created += ensure_page_files_basic(merged_dir, f"{root}/{page}")
            json_dump(app_json_path, app_json)
            created += 1
        stats["registered_existing_pages"] = added
        stats["created"] = created

    stats["sanitized_json_files"] = sanitize_json_warning_files(merged_dir)
    stats["runtime_residue"] = repair_runtime_residue(merged_dir)
    stats["sanitized_wxml"] = sanitize_wxml_files(merged_dir)
    compiled_artifacts = move_compiled_artifacts(merged_dir)
    stats["moved_compiled_artifacts"] = compiled_artifacts["moved"]
    stats["skipped_compiled_artifacts"] = compiled_artifacts["skipped"]
    stats["validation"] = validate_restored_project(merged_dir)
    json_dump(merged_dir / "restore-diagnostics.json", stats)
    return stats


def ensure_page_files(merged_dir: Path, app_config: dict[str, Any], page: str) -> int:
    created = 0
    base = merged_dir / Path(page)
    html_path = base.with_suffix(".html")
    wxml_path = base.with_suffix(".wxml")
    if html_path.exists() and not wxml_path.exists():
        copy_html_to_wxml(html_path)
        created += 1
    if not wxml_path.exists():
        wxml_path.parent.mkdir(parents=True, exist_ok=True)
        wxml_path.write_text("<view></view>\n", encoding="utf-8")
        created += 1

    js_path = base.with_suffix(".js")
    if not js_path.exists():
        js_path.parent.mkdir(parents=True, exist_ok=True)
        js_path.write_text("Page({})\n", encoding="utf-8")
        created += 1

    wxss_path = base.with_suffix(".wxss")
    if not wxss_path.exists():
        wxss_path.parent.mkdir(parents=True, exist_ok=True)
        wxss_path.write_text("", encoding="utf-8")
        created += 1

    json_path = base.with_suffix(".json")
    if not json_path.exists():
        json_dump(json_path, page_json_from_config(app_config, page))
        created += 1
    return created


def ensure_page_files_basic(merged_dir: Path, page: str) -> int:
    created = 0
    base = merged_dir / Path(page)
    defaults = {
        ".js": "Page({})\n",
        ".wxml": "<view></view>\n",
        ".wxss": "",
        ".json": "{}\n",
    }
    for ext, content in defaults.items():
        target = base.with_suffix(ext)
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        created += 1
    return created


def normalize_app_json_after_restore(merged_dir: Path) -> int:
    app_json_path = merged_dir / "app.json"
    app_json = read_json_file(app_json_path)
    if not isinstance(app_json, dict):
        return 0

    pages = [normalize_page_path(str(item)) for item in app_json.get("pages", []) if isinstance(item, str)]
    subpackages = app_json.get("subPackages") or app_json.get("subpackages") or []
    normalized_subpackages: list[dict[str, Any]] = []
    sub_roots: list[str] = []
    if isinstance(subpackages, list):
        for item in subpackages:
            if not isinstance(item, dict) or not isinstance(item.get("root"), str):
                continue
            root = item["root"].strip("/\\")
            if not root:
                continue
            normalized = {key: value for key, value in item.items() if key not in ("pages", "root")}
            normalized["root"] = root
            existing_pages = [
                normalize_page_path(str(page)).replace(root.rstrip("/") + "/", "", 1)
                for page in item.get("pages", [])
                if isinstance(page, str)
            ]
            normalized["pages"] = [page for page in existing_pages if page]
            normalized_subpackages.append(normalized)
            sub_roots.append(root)

    main_pages: list[str] = []
    for page in pages:
        moved = False
        for subpackage in normalized_subpackages:
            root = subpackage["root"].rstrip("/")
            prefix = root + "/"
            if page.startswith(prefix):
                rel_page = page[len(prefix) :]
                if rel_page and rel_page not in subpackage["pages"]:
                    subpackage["pages"].append(rel_page)
                moved = True
                break
        if not moved and not page.startswith("__plugin__/"):
            main_pages.append(page)

    app_json["pages"] = list(dict.fromkeys(main_pages))
    tab_bar = app_json.get("tabBar")
    if tab_bar is not None:
        app_json["tabBar"] = normalize_tab_bar(tab_bar)
    if normalized_subpackages:
        app_json["subPackages"] = [
            {**subpackage, "pages": list(dict.fromkeys(subpackage["pages"]))}
            for subpackage in normalized_subpackages
        ]
        app_json.pop("subpackages", None)

    created = 0
    for page in app_json.get("pages", []):
        created += ensure_page_files_basic(merged_dir, page)
    for subpackage in app_json.get("subPackages", []):
        root = subpackage.get("root", "").strip("/\\")
        for page in subpackage.get("pages", []):
            created += ensure_page_files_basic(merged_dir, f"{root}/{page}")
    json_dump(app_json_path, app_json)
    created += 1
    return created


def move_compiled_file(merged_dir: Path, name: str) -> int:
    source = merged_dir / name
    if not source.exists():
        return 0
    compiled_dir = merged_dir / "_compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)
    target = compiled_dir / name
    if target.exists():
        if file_sha256(source) == file_sha256(target):
            unlink_with_retry(source)
            return 0
        target = compiled_dir / f"{source.stem}_{int(time.time())}{source.suffix}"
    move_with_retry(source, target)
    return 1


def find_wuwxapkg_dir(explicit: str | None = None) -> Path | None:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    env_value = os.environ.get("WUWXAPKG_DIR")
    if env_value:
        candidates.append(Path(env_value))
    candidates.extend(
        [
            DEFAULT_WUWXAPKG_DIR,
            Path(r"D:\Tools\MiniSpy-last\WorkDir\wuWxapkg-1"),
        ]
    )
    for candidate in candidates:
        script = candidate / "wuWxapkg.js"
        modules = candidate / "node_modules"
        if script.exists() and modules.exists():
            return candidate
    return None


def node_available() -> bool:
    return shutil.which("node") is not None


def run_wuwxapkg(wu_dir: Path, wxapkg_file: Path, cwd: Path, extra_args: list[str] | None = None) -> tuple[bool, str]:
    args = ["node", str(wu_dir / "wuWxapkg.js")]
    if extra_args:
        args.extend(extra_args)
    args.append(str(wxapkg_file))
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    return proc.returncode == 0, proc.stdout


def copy_tree(source: Path, destination: Path) -> int:
    copied = 0
    if not source.exists():
        return copied
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    return copied


def restore_with_wuwxapkg(
    output_root: Path,
    packages: list[PackageResult],
    appid: str,
    wu_dir: Path | None = None,
) -> tuple[bool, int, str]:
    resolved_wu_dir = find_wuwxapkg_dir(str(wu_dir) if wu_dir else None)
    if not resolved_wu_dir or not node_available():
        return False, 0, "wuWxapkg unavailable"

    successful = [pkg for pkg in packages if not pkg.error]
    main_packages = [pkg for pkg in successful if pkg.kind == "main"]
    sub_packages = [pkg for pkg in successful if pkg.kind != "main"]
    if not main_packages:
        return False, 0, "main package not found"

    restore_work = output_root / "_restore_work"
    if restore_work.exists():
        shutil.rmtree(restore_work)
    restore_work.mkdir(parents=True, exist_ok=True)

    logs: list[str] = []
    main_pkg = main_packages[0]
    main_wxapkg = restore_work / "__APP__.wxapkg"
    shutil.copy2(main_pkg.decrypted, main_wxapkg)
    ok, log = run_wuwxapkg(resolved_wu_dir, main_wxapkg, restore_work)
    logs.append(log)
    if not ok:
        (output_root / "restore-wuwxapkg.log").write_text("\n".join(logs), encoding="utf-8", errors="replace")
        return False, 0, "main package restore failed"

    restored_main_dir = restore_work / "__APP__"
    if not restored_main_dir.exists():
        (output_root / "restore-wuwxapkg.log").write_text("\n".join(logs), encoding="utf-8", errors="replace")
        return False, 0, "restored main directory not found"

    for pkg in sub_packages:
        sub_name = safe_name(Path(pkg.source).stem)
        sub_wxapkg = restore_work / f"{sub_name}.wxapkg"
        shutil.copy2(pkg.decrypted, sub_wxapkg)
        ok, log = run_wuwxapkg(resolved_wu_dir, sub_wxapkg, restore_work, ["-s=__APP__"])
        logs.append(log)
        sub_restore_root = restore_work / safe_name(Path(sub_wxapkg).stem) / "__APP__"
        if ok and sub_restore_root.exists():
            copy_tree(sub_restore_root, restored_main_dir)

    merged_dir = output_root / "merged"
    if merged_dir.exists():
        shutil.rmtree(merged_dir)
    copied = copy_tree(restored_main_dir, merged_dir)
    postprocess = postprocess_restored_project(merged_dir)
    copied += int(postprocess.get("created", 0) or 0)
    project_config = {
        "appid": appid,
        "projectname": output_root.name,
        "compileType": "miniprogram",
        "libVersion": "latest",
        "setting": {
            "urlCheck": False,
            "es6": True,
            "postcss": True,
            "minified": False,
        },
    }
    json_dump(merged_dir / "project.config.json", project_config)
    copied += 1
    report = {
        "mode": "wuWxapkg",
        "tool": str(resolved_wu_dir),
        "appid_project": str(merged_dir),
        "postprocess": postprocess,
        "notes": [
            "packages 保留 Python 原始独立解包结果。",
            "merged 由 wuWxapkg 对解密后的 wxapkg 做真实工程还原生成。",
        ],
    }
    json_dump(merged_dir / "restore-report.json", report)
    (output_root / "restore-wuwxapkg.log").write_text("\n".join(logs), encoding="utf-8", errors="replace")
    shutil.rmtree(restore_work, ignore_errors=True)
    return True, copied + 1, str(resolved_wu_dir)


def restore_devtools_project(output_root: Path, appid: str) -> int:
    merged_dir = output_root / "merged"
    app_config_path = merged_dir / "app-config.json"
    app_config = read_json_file(app_config_path)
    if not isinstance(app_config, dict):
        return 0

    created = 0
    app_json = build_app_json(app_config)
    json_dump(merged_dir / "app.json", app_json)
    created += 1

    project_config = {
        "appid": appid,
        "projectname": appid,
        "compileType": "miniprogram",
        "libVersion": "latest",
        "setting": {
            "urlCheck": False,
            "es6": True,
            "postcss": True,
            "minified": False,
        },
    }
    json_dump(merged_dir / "project.config.json", project_config)
    created += 1

    if not (merged_dir / "app.js").exists():
        app_service = merged_dir / "app-service.js"
        if app_service.exists():
            shutil.copy2(app_service, merged_dir / "app.js")
        else:
            (merged_dir / "app.js").write_text("App({})\n", encoding="utf-8")
        created += 1

    if not (merged_dir / "app.wxss").exists():
        app_wxss = merged_dir / "app-wxss.js"
        if app_wxss.exists():
            (merged_dir / "app.wxss").write_text("/* restored from compiled wxss runtime */\n", encoding="utf-8")
        else:
            (merged_dir / "app.wxss").write_text("", encoding="utf-8")
        created += 1

    pages = app_json.get("pages")
    if isinstance(pages, list):
        for page in pages:
            if isinstance(page, str):
                created += ensure_page_files(merged_dir, app_config, page)

    subpackages = app_json.get("subPackages")
    if isinstance(subpackages, list):
        for subpackage in subpackages:
            if not isinstance(subpackage, dict) or not isinstance(subpackage.get("root"), str):
                continue
            root = subpackage["root"].strip("/\\")
            for page in subpackage.get("pages", []):
                if isinstance(page, str):
                    created += ensure_page_files(merged_dir, app_config, f"{root}/{page}")

    for html_path in list(merged_dir.rglob("*.html")):
        if "_compiled" in html_path.parts:
            continue
        wxml_path = html_path.with_suffix(".wxml")
        if not wxml_path.exists():
            copy_html_to_wxml(html_path)
            created += 1

    for name in ("app-config.json", "app-service.js", "app-wxss.js", "page-frame.js", "page-frame.html"):
        created += move_compiled_file(merged_dir, name)

    postprocess = postprocess_restored_project(merged_dir)
    created += int(postprocess.get("created", 0) or 0)

    restore_report = {
        "mode": "devtools-project",
        "appid": appid,
        "app_json": "app.json",
        "source_config": "_compiled/app-config.json",
        "postprocess": postprocess,
        "notes": [
            "packages 保留原始解包结果。",
            "merged 是基于编译产物生成的开发者工具工程目录。",
            "wxml 由 wxapkg 内 html 页面复制生成，js/wxss 在缺失时使用占位文件。",
        ],
    }
    json_dump(merged_dir / "restore-report.json", restore_report)
    created += 1
    return created


def merge_packages(output_root: Path, packages: list[PackageResult]) -> tuple[int, int]:
    merged_dir = output_root / "merged"
    conflicts_dir = output_root / "_conflicts"
    merged_dir.mkdir(parents=True, exist_ok=True)
    conflicts_dir.mkdir(parents=True, exist_ok=True)

    merged = 0
    conflicts = 0
    successful = [pkg for pkg in packages if not pkg.error]
    main_packages = [pkg for pkg in successful if pkg.kind == "main"]
    sub_packages = [pkg for pkg in successful if pkg.kind != "main"]

    for pkg in main_packages + sub_packages:
        source = Path(pkg.output)
        copied, conflicted = copy_tree_with_conflicts(
            source,
            merged_dir,
            conflicts_dir / safe_name(pkg.label),
            pkg.merge_prefix,
        )
        merged += copied
        conflicts += conflicted
    return merged, conflicts


def write_log(output_root: Path, lines: list[str]) -> None:
    (output_root / "unpack.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def process(appid: str, output_root: Path, applet_root: Path) -> RunResult:
    app_dir = select_package_dir(find_app_dir(applet_root, appid))
    output_root.mkdir(parents=True, exist_ok=True)
    decrypted_root = output_root / "decrypted"
    packages_root = output_root / "packages"
    decrypted_root.mkdir(parents=True, exist_ok=True)
    packages_root.mkdir(parents=True, exist_ok=True)

    wxapkg_files = collect_wxapkg_files(app_dir)
    result = RunResult(
        appid=appid,
        applet_root=str(applet_root),
        matched_dir=str(app_dir),
        output_root=str(output_root),
        wxapkg_count=len(wxapkg_files),
    )
    log_lines = [
        f"started_at={time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"appid={appid}",
        f"applet_root={applet_root}",
        f"matched_dir={app_dir}",
        f"output_root={output_root}",
        f"wxapkg_count={len(wxapkg_files)}",
    ]

    main_dir: Path | None = None
    pending_roots: list[str] = []
    temporary_outputs: list[tuple[PackageResult, list[str]]] = []

    for index, source in enumerate(wxapkg_files, 1):
        label = safe_name(source.stem or f"package_{index}")
        decrypted_path = decrypted_root / f"{index:02d}_{label}.wxapkg"
        package_dir = unique_dir(packages_root, f"{index:02d}_{label}")
        package_result = PackageResult(
            source=str(source),
            decrypted=str(decrypted_path),
            output=str(package_dir),
            label=package_dir.name,
            kind="sub",
            file_count=0,
        )
        try:
            raw = source.read_bytes()
            decoded = decrypt_wxapkg(raw, appid) if looks_encrypted(raw) else raw
            decrypted_path.write_bytes(decoded)
            files = unpack_wxapkg(decoded, package_dir)
            kind = classify_package(package_dir, files)
            package_result.kind = kind
            package_result.file_count = len(files)
            temporary_outputs.append((package_result, files))
            if kind == "main" and main_dir is None:
                main_dir = package_dir
                pending_roots = load_subpackage_roots(main_dir)
            log_lines.append(f"ok {source} -> {package_dir} files={len(files)} kind={kind}")
        except Exception as exc:
            package_result.error = str(exc)
            result.failed += 1
            log_lines.append(f"failed {source}: {exc}")
        result.packages.append(package_result)

    roots = pending_roots
    if main_dir is None:
        for package_result, files in temporary_outputs:
            if package_result.kind == "main":
                main_dir = Path(package_result.output)
                roots = load_subpackage_roots(main_dir)
                break

    for package_result, files in temporary_outputs:
        if package_result.kind != "main":
            existing_root = detect_package_root(files, roots)
            inferred_root = infer_package_root_from_source(package_result, roots) if not existing_root else ""
            package_result.package_root = existing_root or inferred_root
            if not existing_root:
                package_result.merge_prefix = inferred_root or f"_subpackages/{safe_name(package_result.label)}"

    wu_ok, wu_restored, wu_engine = restore_with_wuwxapkg(output_root, result.packages, appid)
    if wu_ok:
        result.restored_files = wu_restored
        result.restore_engine = f"wuWxapkg:{wu_engine}"
        result.merged_files = count_files(output_root / "merged")
        result.conflicts = 0
    else:
        result.merged_files, result.conflicts = merge_packages(output_root, result.packages)
        result.restored_files = restore_devtools_project(output_root, appid)
        result.restore_engine = f"python-basic:{wu_engine}"
    manifest = {
        "appid": result.appid,
        "applet_root": result.applet_root,
        "matched_dir": result.matched_dir,
        "output_root": result.output_root,
        "wxapkg_count": result.wxapkg_count,
        "merged_files": result.merged_files,
        "conflicts": result.conflicts,
        "restored_files": result.restored_files,
        "restore_engine": result.restore_engine,
        "failed": result.failed,
        "packages": [package.__dict__ for package in result.packages],
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_log(output_root, log_lines)
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Decrypt and unpack Windows WeChat Mini Program wxapkg files.")
    parser.add_argument("appid", help="Mini Program appid, for example wx1234567890abcdef")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--applet-root", help="Override WECHAT_APPLET_ROOT from scripts/.env")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    env = load_env(SCRIPT_DIR / ".env")
    applet_root_value = args.applet_root or env.get("WECHAT_APPLET_ROOT") or os.environ.get("WECHAT_APPLET_ROOT")
    if not applet_root_value:
        print("error: missing WECHAT_APPLET_ROOT, configure scripts/.env or pass --applet-root", file=sys.stderr)
        return 2

    try:
        result = process(args.appid, Path(args.out).resolve(), Path(applet_root_value).expanduser())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"appid: {result.appid}")
    print(f"wxapkg: {result.wxapkg_count}")
    print(f"packages: {len(result.packages)}")
    print(f"files: {result.merged_files}")
    print(f"merged: {Path(result.output_root) / 'merged'}")
    print(f"restored: {result.restored_files}")
    print(f"engine: {result.restore_engine}")
    print(f"conflicts: {result.conflicts}")
    print(f"failed: {result.failed}")
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
