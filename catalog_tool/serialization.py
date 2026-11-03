"""Addressables ContentCatalogData serialized object codec (JSON catalog / v1 keys)."""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, BinaryIO, Optional


class ObjectType(IntEnum):
    ASCII_STRING = 0
    UNICODE_STRING = 1
    UINT16 = 2
    UINT32 = 3
    INT32 = 4
    HASH128 = 5
    TYPE = 6
    JSON_OBJECT = 7


ABRO_CLASS = "UnityEngine.ResourceManagement.ResourceProviders.AssetBundleRequestOptions"
ABRO_ASM = "UnityEngine.ResourceManagement, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null"


def read_string1(f: BinaryIO) -> str:
    length = struct.unpack("<B", f.read(1))[0]
    return f.read(length).decode("ascii")


def read_string4_ascii(f: BinaryIO) -> str:
    (length,) = struct.unpack("<i", f.read(4))
    return f.read(length).decode("ascii")


def read_string4_unicode(f: BinaryIO) -> str:
    (length,) = struct.unpack("<i", f.read(4))
    return f.read(length).decode("utf-16-le")


def write_string1(f: BinaryIO, s: str) -> None:
    b = s.encode("ascii")
    if len(b) > 255:
        raise ValueError("string1 too long")
    f.write(struct.pack("<B", len(b)))
    f.write(b)


def write_string4_ascii(f: BinaryIO, s: str) -> None:
    b = s.encode("ascii")
    f.write(struct.pack("<i", len(b)))
    f.write(b)


def write_string4_unicode(f: BinaryIO, s: str) -> None:
    b = s.encode("utf-16-le")
    f.write(struct.pack("<i", len(b)))
    f.write(b)


def _parse_abro(json_text: str) -> dict[str, Any]:
    data = json.loads(json_text)
    return {
        "kind": "AssetBundleRequestOptions",
        "json_text": json_text,
        "data": data,
    }


def decode_object_v1(data: bytes, offset: int = 0) -> tuple[Any, bytes]:
    """Decode one serialized object; return (value, raw_bytes)."""
    start = offset
    import io

    f = io.BytesIO(data)
    f.seek(offset)
    type_byte = struct.unpack("<B", f.read(1))[0]
    obj_type = ObjectType(type_byte)

    if obj_type == ObjectType.ASCII_STRING:
        val = read_string4_ascii(f)
    elif obj_type == ObjectType.UNICODE_STRING:
        val = read_string4_unicode(f)
    elif obj_type == ObjectType.UINT16:
        val = struct.unpack("<H", f.read(2))[0]
    elif obj_type == ObjectType.UINT32:
        val = struct.unpack("<I", f.read(4))[0]
    elif obj_type == ObjectType.INT32:
        val = struct.unpack("<i", f.read(4))[0]
    elif obj_type == ObjectType.HASH128:
        val = {"kind": "Hash128", "value": read_string1(f)}
    elif obj_type == ObjectType.TYPE:
        val = {"kind": "TypeReference", "value": read_string1(f)}
    elif obj_type == ObjectType.JSON_OBJECT:
        asm = read_string1(f)
        cls = read_string1(f)
        json_text = read_string4_unicode(f)
        if cls == ABRO_CLASS:
            val = _parse_abro(json_text)
            val["assembly"] = asm
            val["class_name"] = cls
        else:
            val = {
                "kind": "JsonObject",
                "assembly": asm,
                "class_name": cls,
                "json_text": json_text,
            }
    else:
        raise ValueError(f"Unknown ObjectType {type_byte} at offset {offset}")

    end = f.tell()
    return val, data[start:end]


def encode_object_v1(value: Any) -> bytes:
    import io

    f = io.BytesIO()
    if isinstance(value, str):
        try:
            value.encode("ascii")
            f.write(struct.pack("<B", ObjectType.ASCII_STRING))
            write_string4_ascii(f, value)
        except UnicodeEncodeError:
            f.write(struct.pack("<B", ObjectType.UNICODE_STRING))
            write_string4_unicode(f, value)
    elif isinstance(value, int):
        if -(2**31) <= value < 2**31:
            f.write(struct.pack("<B", ObjectType.INT32))
            f.write(struct.pack("<i", value))
        elif 0 <= value < 2**32:
            f.write(struct.pack("<B", ObjectType.UINT32))
            f.write(struct.pack("<I", value))
        else:
            raise ValueError(f"int out of range: {value}")
    elif isinstance(value, dict):
        kind = value.get("kind")
        if kind == "Hash128":
            f.write(struct.pack("<B", ObjectType.HASH128))
            write_string1(f, value["value"])
        elif kind == "TypeReference":
            f.write(struct.pack("<B", ObjectType.TYPE))
            write_string1(f, value["value"])
        elif kind == "AssetBundleRequestOptions":
            f.write(struct.pack("<B", ObjectType.JSON_OBJECT))
            write_string1(f, value.get("assembly", ABRO_ASM))
            write_string1(f, value.get("class_name", ABRO_CLASS))
            json_text = value.get("json_text")
            if json_text is None:
                json_text = json.dumps(value["data"], separators=(",", ":"), ensure_ascii=False)
            write_string4_unicode(f, json_text)
        elif kind == "JsonObject":
            f.write(struct.pack("<B", ObjectType.JSON_OBJECT))
            write_string1(f, value["assembly"])
            write_string1(f, value["class_name"])
            write_string4_unicode(f, value["json_text"])
        else:
            raise ValueError(f"Unknown dict kind {kind!r}")
    else:
        raise TypeError(f"Cannot encode {type(value)!r}")

    return f.getvalue()


def key_to_display(key: Any) -> str:
    if isinstance(key, str):
        return key
    if isinstance(key, int):
        return str(key)
    if isinstance(key, dict):
        if key.get("kind") == "Hash128":
            return f"Hash128:{key['value']}"
        if key.get("kind") == "TypeReference":
            return f"Type:{key['value']}"
    return repr(key)


def abro_set_crc_zero(abro: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ABRO serialized object with CRC disabled."""
    out = dict(abro)
    data = dict(out.get("data") or json.loads(out["json_text"]))
    data["m_Crc"] = 0
    data["m_UseCrcForCachedBundles"] = False
    out["data"] = data
    out["json_text"] = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return out


def abro_update_bundle(abro: dict[str, Any], *, bundle_name: str | None = None, bundle_hash: str | None = None, crc: int | None = None) -> dict[str, Any]:
    out = dict(abro)
    data = dict(out.get("data") or json.loads(out["json_text"]))
    if bundle_name is not None:
        data["m_BundleName"] = bundle_name
    if bundle_hash is not None:
        data["m_Hash"] = bundle_hash
    if crc is not None:
        data["m_Crc"] = crc
    out["data"] = data
    out["json_text"] = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return out
