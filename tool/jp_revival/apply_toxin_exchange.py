#!/usr/bin/env python3
"""Build the JP cash-to-Toxin exchange assets without modifying source files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


JP_LIBRARY_SHA256 = "e0fbd1736894a0bd87f2ba0db930a47db9e110a5f2015ddb2e594add3ab30433"
PATCH_OFFSET = 0x113B88
ORIGINAL_TYPE10_BLOCK = bytes.fromhex("e2 68 9b 6d 91 59 cb 18 93 51 c8 e2")
PATCHED_TYPE10_BLOCK = bytes.fromhex("e0 68 99 6d 00 22 16 f1 07 fa c8 e2")

EXCHANGES = (
    {
        "index": 182,
        "source_price": 10,
        "source_amount": 10_000,
        "name": "10 Toxin",
        "price": 20_000,
        "amount": 10,
    },
    {
        "index": 183,
        "source_price": 25,
        "source_amount": 50_000,
        "name": "30 Toxin",
        "price": 50_000,
        "amount": 30,
    },
    {
        "index": 184,
        "source_price": 100,
        "source_amount": 250_000,
        "name": "175 Toxin",
        "price": 250_000,
        "amount": 175,
    },
    {
        "index": 185,
        "source_price": 350,
        "source_amount": 1_000_000,
        "name": "750 Toxin",
        "price": 1_000_000,
        "amount": 750,
    },
)


class PatchError(ValueError):
    """Raised when an input does not match the verified JP 1.7.0 source."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_native_library(data: bytes, *, verify_hash: bool = True) -> bytes:
    if verify_hash and sha256(data) != JP_LIBRARY_SHA256:
        raise PatchError(
            "native library SHA-256 does not match the preserved JP 1.7.0 build"
        )

    end = PATCH_OFFSET + len(ORIGINAL_TYPE10_BLOCK)
    if len(data) < end:
        raise PatchError("native library is shorter than the verified patch offset")
    if data[PATCH_OFFSET:end] != ORIGINAL_TYPE10_BLOCK:
        raise PatchError(
            f"unexpected bytes at file offset 0x{PATCH_OFFSET:x}; refusing to patch"
        )

    patched = bytearray(data)
    patched[PATCH_OFFSET:end] = PATCHED_TYPE10_BLOCK
    return bytes(patched)


def patch_furniture(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(records) != 835:
        raise PatchError(
            f"expected 835 JP furniture records, found {len(records)}"
        )

    result = [record.copy() for record in records]
    for exchange in EXCHANGES:
        index = exchange["index"]
        record = result[index]
        expected = {
            "Price": exchange["source_price"],
            "Type": 10,
            "BuyMoneyAmount": exchange["source_amount"],
        }
        actual = {key: record.get(key) for key in expected}
        if actual != expected or record.get("PurchaseWithToxin") is not True:
            raise PatchError(
                f"furniture row {index} is not the verified vanilla cash pack: "
                f"expected {expected} with PurchaseWithToxin=true, "
                f"found {actual} with PurchaseWithToxin="
                f"{record.get('PurchaseWithToxin')!r}"
            )

        record["Name"] = exchange["name"]
        record["Price"] = exchange["price"]
        record["PurchaseWithToxin"] = False
        record["BuyMoneyAmount"] = exchange["amount"]
        record["Description"] = (
            f"Exchange ${exchange['price']:,} cash for "
            f"{exchange['amount']} Toxin."
        )

    return result


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temp:
        temp.write(data)
        temp_path = Path(temp.name)
    try:
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def build_outputs(native_path: Path, furniture_path: Path, output_dir: Path) -> dict[str, Any]:
    native_source = native_path.read_bytes()
    furniture_source = furniture_path.read_bytes()

    try:
        furniture_records = json.loads(furniture_source)
    except json.JSONDecodeError as exc:
        raise PatchError(f"invalid furniture JSON: {exc}") from exc
    if not isinstance(furniture_records, list) or not all(
        isinstance(record, dict) for record in furniture_records
    ):
        raise PatchError("furniture JSON must be an array of records")

    patched_native = patch_native_library(native_source)
    patched_furniture = patch_furniture(furniture_records)
    furniture_output = (
        json.dumps(patched_furniture, ensure_ascii=False, indent=4) + "\n"
    ).encode()

    native_output_path = output_dir / "libZombieCafeAndroid.so"
    furniture_output_path = output_dir / "furnitureData.bin.mid.json"
    manifest_path = output_dir / "toxin_exchange_manifest.json"

    manifest = {
        "source_native_sha256": sha256(native_source),
        "patched_native_sha256": sha256(patched_native),
        "source_furniture_sha256": sha256(furniture_source),
        "patched_furniture_sha256": sha256(furniture_output),
        "native_patch_file_offset": f"0x{PATCH_OFFSET:x}",
        "native_original_bytes": ORIGINAL_TYPE10_BLOCK.hex(" "),
        "native_patched_bytes": PATCHED_TYPE10_BLOCK.hex(" "),
        "exchange_rows": [dict(exchange) for exchange in EXCHANGES],
    }

    atomic_write(native_output_path, patched_native)
    atomic_write(furniture_output_path, furniture_output)
    atomic_write(
        manifest_path,
        (json.dumps(manifest, indent=4) + "\n").encode(),
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create JP 1.7.0 cash-to-Toxin exchange patch outputs."
    )
    parser.add_argument("--native-lib", required=True, type=Path)
    parser.add_argument("--furniture-json", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build_outputs(
            args.native_lib, args.furniture_json, args.output_dir
        )
    except (OSError, PatchError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(
        "Created verified JP Toxin exchange outputs; patched native SHA-256: "
        + manifest["patched_native_sha256"]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
