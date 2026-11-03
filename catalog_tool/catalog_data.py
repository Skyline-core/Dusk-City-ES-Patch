"""Decode / encode Unity Addressables ContentCatalogData (JSON catalog format)."""

from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import struct
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    from .serialization import (
        abro_set_crc_zero,
        abro_update_bundle,
        decode_object_v1,
        encode_object_v1,
        key_to_display,
    )
except ImportError:
    from serialization import (
        abro_set_crc_zero,
        abro_update_bundle,
        decode_object_v1,
        encode_object_v1,
        key_to_display,
    )


@dataclass
class ResourceType:
    assembly_name: str
    class_name: str

    @staticmethod
    def from_json(j: dict) -> "ResourceType":
        return ResourceType(j["m_AssemblyName"], j["m_ClassName"])

    def to_json(self) -> dict:
        return {"m_AssemblyName": self.assembly_name, "m_ClassName": self.class_name}


@dataclass
class Location:
    internal_id: str
    provider_id: str
    dependency_key: Any
    extra_data: Any
    dependency_hash: int
    primary_key: Any
    resource_type: Optional[ResourceType]
    # Preserve exact extra-data bytes when unchanged (round-trip / re-encode)
    extra_data_raw: Optional[bytes] = None
    entry_index: int = -1

    def copy_mapped(
        self,
        map_str: Any,
        *,
        extra_data: Any | None = None,
        extra_data_raw: Optional[bytes] = None,
    ) -> "Location":
        return Location(
            internal_id=map_str(self.internal_id),
            provider_id=self.provider_id,
            dependency_key=_map_key(self.dependency_key, map_str),
            extra_data=extra_data if extra_data is not None else _map_extra(self.extra_data, map_str),
            dependency_hash=self.dependency_hash,
            primary_key=_map_key(self.primary_key, map_str),
            resource_type=self.resource_type,
            extra_data_raw=extra_data_raw,
        )


def _map_key(key: Any, map_str) -> Any:
    if key is None:
        return None
    if isinstance(key, str):
        return map_str(key)
    if isinstance(key, dict):
        if key.get("kind") == "Hash128":
            return key  # GUID keys stay unless caller replaces buckets separately
        if key.get("kind") == "TypeReference":
            return key
        if key.get("kind") == "JsonObject":
            k = copy.deepcopy(key)
            return k
    return key


def _map_extra(extra: Any, map_str) -> Any:
    if extra is None:
        return None
    if isinstance(extra, dict) and extra.get("kind") == "AssetBundleRequestOptions":
        data = copy.deepcopy(extra.get("data") or json.loads(extra["json_text"]))
        for fld in ("m_BundleName", "m_Hash"):
            if fld in data and isinstance(data[fld], str):
                data[fld] = map_str(data[fld])
        out = dict(extra)
        out["data"] = data
        out["json_text"] = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return out
    return extra


@dataclass
class Bucket:
    key: Any
    key_raw: bytes
    entry_indices: list[int]


@dataclass
class Catalog:
    raw: dict
    provider_ids: list[str]
    internal_ids: list[str]
    resource_types: list[ResourceType]
    internal_id_prefixes: list[str]
    locations: list[Location]
    buckets: list[Bucket]
    keys: list[Any]
    _original_blobs: dict[str, str] = field(default_factory=dict)
    dirty: bool = False

    @staticmethod
    def load_json(path: str) -> "Catalog":
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        return Catalog.from_raw(raw)

    @staticmethod
    def from_raw(raw: dict) -> "Catalog":
        cat = Catalog(
            raw=raw,
            provider_ids=list(raw["m_ProviderIds"]),
            internal_ids=list(raw["m_InternalIds"]),
            resource_types=[ResourceType.from_json(x) for x in raw["m_resourceTypes"]],
            internal_id_prefixes=list(raw.get("m_InternalIdPrefixes") or []),
            locations=[],
            buckets=[],
            keys=[],
            _original_blobs={
                "m_KeyDataString": raw["m_KeyDataString"],
                "m_BucketDataString": raw["m_BucketDataString"],
                "m_EntryDataString": raw["m_EntryDataString"],
                "m_ExtraDataString": raw["m_ExtraDataString"],
            },
        )
        cat._decode_binary()
        return cat

    def resolve_internal_id(self, stored: str) -> str:
        if not self.internal_id_prefixes:
            return stored
        split_index = stored.find("#")
        if split_index != -1:
            prefix_part = stored[:split_index]
            if prefix_part.isdigit():
                idx = int(prefix_part)
                if 0 <= idx < len(self.internal_id_prefixes):
                    return self.internal_id_prefixes[idx] + stored[split_index + 1 :]
        return stored

    def _decode_binary(self) -> None:
        bucket_bytes = base64.b64decode(self.raw["m_BucketDataString"])
        key_bytes = base64.b64decode(self.raw["m_KeyDataString"])
        entry_bytes = base64.b64decode(self.raw["m_EntryDataString"])
        extra_bytes = base64.b64decode(self.raw["m_ExtraDataString"])

        buckets_meta: list[tuple[int, list[int]]] = []
        bf = io.BytesIO(bucket_bytes)
        (bucket_count,) = struct.unpack("<i", bf.read(4))
        for _ in range(bucket_count):
            (offset,) = struct.unpack("<i", bf.read(4))
            (entry_count,) = struct.unpack("<i", bf.read(4))
            entries = list(struct.unpack(f"<{entry_count}i", bf.read(4 * entry_count)))
            buckets_meta.append((offset, entries))

        kf = io.BytesIO(key_bytes)
        (key_count,) = struct.unpack("<i", kf.read(4))
        if key_count != bucket_count:
            raise ValueError(f"key count {key_count} != bucket count {bucket_count}")

        keys: list[Any] = []
        key_raws: list[bytes] = []
        for offset, _ in buckets_meta:
            key_obj, key_raw = decode_object_v1(key_bytes, offset)
            keys.append(key_obj)
            key_raws.append(key_raw)

        ef = io.BytesIO(entry_bytes)
        (entry_count,) = struct.unpack("<i", ef.read(4))
        locations: list[Location] = []
        for idx in range(entry_count):
            fields = struct.unpack("<7i", ef.read(28))
            (
                internal_id_index,
                provider_index,
                dependency_key_index,
                dep_hash,
                data_index,
                primary_key_index,
                resource_type_index,
            ) = fields
            internal_id = self.resolve_internal_id(self.internal_ids[internal_id_index])
            provider_id = self.provider_ids[provider_index]
            dependency_key = keys[dependency_key_index] if dependency_key_index >= 0 else None
            primary_key = keys[primary_key_index]
            resource_type = (
                self.resource_types[resource_type_index] if resource_type_index >= 0 else None
            )
            extra_data = None
            extra_raw = None
            if data_index >= 0:
                extra_data, extra_raw = decode_object_v1(extra_bytes, data_index)
            locations.append(
                Location(
                    internal_id=internal_id,
                    provider_id=provider_id,
                    dependency_key=dependency_key,
                    extra_data=extra_data,
                    dependency_hash=dep_hash,
                    primary_key=primary_key,
                    resource_type=resource_type,
                    extra_data_raw=extra_raw,
                    entry_index=idx,
                )
            )

        self.locations = locations
        self.keys = keys
        self.buckets = [
            Bucket(key=keys[i], key_raw=key_raws[i], entry_indices=entries)
            for i, (_, entries) in enumerate(buckets_meta)
        ]

    def resources_by_key(self) -> dict[Any, list[Location]]:
        out: dict[Any, list[Location]] = {}
        for b in self.buckets:
            out[b.key] = [self.locations[i] for i in b.entry_indices]
        return out

    def encode_blobs(self) -> dict[str, str]:
        if not self.dirty:
            return dict(self._original_blobs)
        return self._encode_blobs_clean()

    def _encode_blobs_clean(self) -> dict[str, str]:
        """Rebuild catalog binary tables (used when dirty)."""

        def kid(k: Any) -> Any:
            if isinstance(k, dict):
                return (
                    k.get("kind"),
                    k.get("value"),
                    k.get("assembly"),
                    k.get("class_name"),
                    k.get("json_text"),
                )
            return k

        key_bytes = io.BytesIO()
        key_bytes.write(struct.pack("<i", len(self.buckets)))
        key_offsets: list[int] = []
        for b in self.buckets:
            key_offsets.append(key_bytes.tell())
            if b.key_raw:
                key_bytes.write(b.key_raw)
            else:
                key_bytes.write(encode_object_v1(b.key))

        key_index = {kid(b.key): i for i, b in enumerate(self.buckets)}

        extra_stream = io.BytesIO()
        entry_stream = io.BytesIO()
        entry_stream.write(struct.pack("<i", len(self.locations)))

        internal_id_list = list(self.internal_ids)
        id_idx = {s: i for i, s in enumerate(internal_id_list)}

        def intern_id(s: str) -> int:
            if s not in id_idx:
                id_idx[s] = len(internal_id_list)
                internal_id_list.append(s)
            return id_idx[s]

        prov_list = list(self.provider_ids)
        p_idx = {s: i for i, s in enumerate(prov_list)}

        def intern_prov(s: str) -> int:
            if s not in p_idx:
                p_idx[s] = len(prov_list)
                prov_list.append(s)
            return p_idx[s]

        rt_list = list(self.resource_types)
        rt_idx = {(r.assembly_name, r.class_name): i for i, r in enumerate(rt_list)}

        def intern_rt(rt: Optional[ResourceType]) -> int:
            if rt is None:
                return -1
            k = (rt.assembly_name, rt.class_name)
            if k not in rt_idx:
                rt_idx[k] = len(rt_list)
                rt_list.append(rt)
            return rt_idx[k]

        for loc in self.locations:
            data_index = -1
            if loc.extra_data is not None:
                data_index = extra_stream.tell()
                extra_stream.write(encode_object_v1(loc.extra_data))
            elif loc.extra_data_raw:
                data_index = extra_stream.tell()
                extra_stream.write(loc.extra_data_raw)

            pk = loc.primary_key
            pk_idx = key_index.get(kid(pk))
            if pk_idx is None:
                raise ValueError(f"Primary key not in bucket keys: {key_to_display(pk)}")

            dep_idx = -1
            if loc.dependency_key is not None:
                dep_idx = key_index.get(kid(loc.dependency_key))
                if dep_idx is None:
                    raise ValueError(
                        f"Dependency key not in bucket keys: {key_to_display(loc.dependency_key)}"
                    )

            entry_stream.write(
                struct.pack(
                    "<7i",
                    intern_id(loc.internal_id),
                    intern_prov(loc.provider_id),
                    dep_idx,
                    loc.dependency_hash,
                    data_index,
                    pk_idx,
                    intern_rt(loc.resource_type),
                )
            )

        bucket_stream = io.BytesIO()
        bucket_stream.write(struct.pack("<i", len(self.buckets)))
        for i, b in enumerate(self.buckets):
            bucket_stream.write(struct.pack("<i", key_offsets[i]))
            bucket_stream.write(struct.pack("<i", len(b.entry_indices)))
            for e in b.entry_indices:
                bucket_stream.write(struct.pack("<i", e))

        self.provider_ids = prov_list
        self.internal_ids = internal_id_list
        self.resource_types = rt_list

        return {
            "m_KeyDataString": base64.b64encode(key_bytes.getvalue()).decode("ascii"),
            "m_BucketDataString": base64.b64encode(bucket_stream.getvalue()).decode("ascii"),
            "m_EntryDataString": base64.b64encode(entry_stream.getvalue()).decode("ascii"),
            "m_ExtraDataString": base64.b64encode(extra_stream.getvalue()).decode("ascii"),
        }

    def to_json_dict(self) -> dict:
        out = copy.deepcopy(self.raw)
        if self.dirty:
            blobs = self._encode_blobs_clean()
            out.update(blobs)
            out["m_ProviderIds"] = self.provider_ids
            out["m_InternalIds"] = self.internal_ids
            out["m_resourceTypes"] = [r.to_json() for r in self.resource_types]
        return out

    def save_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_json_dict(), f, ensure_ascii=False, separators=(",", ":"))

    def verify_roundtrip_blobs(self) -> dict[str, bool]:
        if self.dirty:
            blobs = self._encode_blobs_clean()
        else:
            blobs = self._original_blobs
        return {
            k: blobs[k] == self._original_blobs[k]
            for k in self._original_blobs
        }


# --- Locale clone helpers ---

DEFAULT_EN_BUNDLE = (
    "{UnityEngine.AddressableAssets.Addressables.RuntimePath}\\StandaloneWindows64\\"
    "localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle"
)

EN_ASSETS_BUNDLE_KEY = (
    "localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle"
)
EN_STRING_BUNDLE_KEY = (
    "localization-string-tables-english(en)_assets_all_8954925c0a0a01594b219a56b187846d.bundle"
)
EN_ASSET_TABLES_BUNDLE_KEY = (
    "localization-asset-tables-english(en)_assets_all_9084a065f856188b8e08f2a2458337b7.bundle"
)

# Runtime bundle paths patched in phase-1 hijack-en (catalog internalId suffixes)
HIJACK_EN_BUNDLE_PATH_MARKERS = (
    "localization-string-tables-english(en)_assets_all.bundle",
    "localization-asset-tables-english(en)_assets_all.bundle",
    "localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle",
    # Locales bundle: patched so the 'English (en)' menu entry reads 'Español'
    "localization-locales_assets_all.bundle",
)

BUNDLE_PROVIDER = "UnityEngine.ResourceManagement.ResourceProviders.AssetBundleProvider"


def _key_fingerprint(key: Any) -> Any:
    if isinstance(key, dict):
        return (key.get("kind"), key.get("value"))
    return key


def make_es_string_mapper(
    bundle_map: dict[str, str] | None = None,
    bundle_key_map: dict[str, str] | None = None,
) -> Any:
    bundle_map = bundle_map or {}
    bundle_key_map = bundle_key_map or {}

    def subst(s: str) -> str:
        if s in bundle_map:
            return bundle_map[s]
        if s in bundle_key_map:
            return bundle_key_map[s]
        rules = [
            ("Locale-en", "Locale-es"),
            ("English (en)", "Spanish (es)"),
            ("english(en)", "spanish(es)"),
            ("Translation_en", "Translation_es"),
            ("Image_en", "Image_es"),
            ("_EN.json", "_ES.json"),
            ("_EN.png", "_ES.png"),
            ("_EN", "_ES"),
        ]
        out = s
        for a, b in rules:
            out = out.replace(a, b)
        return out

    return subst


def _hash128_for_es(en_key: dict) -> dict:
    digest = hashlib.md5(f"es:{en_key['value']}".encode()).hexdigest()
    return {"kind": "Hash128", "value": digest}


def _location_is_en_localize_asset(internal_id: str) -> bool:
    return internal_id in (
        "Assets/Localize/English (en).asset",
        "Assets/Localize/Translation_en.asset",
        "Assets/Localize/Image_en.asset",
    )


def bucket_is_en_clone_source(bucket: Bucket, cat: Catalog, mapper) -> bool:
    key = bucket.key
    if isinstance(key, str):
        if key == "Locale":
            return False
        if key in ("Locale-en", "English (en)", "Translation_en", "Image_en"):
            return True
        if key.endswith("_EN"):
            return True
        if "english(en)" in key.lower():
            return True
        if mapper(key) != key:
            return True
    if isinstance(key, dict) and key.get("kind") == "Hash128":
        return any(_location_is_en_localize_asset(cat.locations[i].internal_id) for i in bucket.entry_indices)
    return False


def _mapped_new_bucket_key(old_key: Any, mapper) -> Any:
    if isinstance(old_key, str):
        return mapper(old_key)
    if isinstance(old_key, dict) and old_key.get("kind") == "Hash128":
        return _hash128_for_es(old_key)
    return old_key


def _prepare_extra(
    src: Location,
    mapper,
    bundle_map: dict[str, str],
    bundle_hashes: dict[str, str],
    zero_crc: bool,
) -> Any:
    extra = src.extra_data
    if not isinstance(extra, dict) or extra.get("kind") != "AssetBundleRequestOptions":
        return extra
    extra = copy.deepcopy(extra)
    if zero_crc:
        extra = abro_set_crc_zero(extra)
    data = extra.get("data") or json.loads(extra["json_text"])
    bn = data.get("m_BundleName", "")
    if bn in bundle_hashes:
        extra = abro_update_bundle(extra, bundle_hash=bundle_hashes[bn])
    mapped_iid = mapper(src.internal_id)
    if mapped_iid in bundle_map:
        bname = bundle_map[mapped_iid].split("\\")[-1].replace(".bundle", "")
        extra = abro_update_bundle(extra, bundle_name=bname)
    return extra


def clone_locale(
    cat: Catalog,
    from_locale: str = "en",
    to_locale: str = "es",
    bundle_map: dict[str, str] | None = None,
    bundle_hashes: dict[str, str] | None = None,
    zero_crc_bundles: bool = True,
) -> Catalog:
    if from_locale != "en" or to_locale != "es":
        raise NotImplementedError("Only en -> es is implemented for this game catalog")

    bundle_map = dict(bundle_map or {})
    bundle_hashes = bundle_hashes or {}
    runtime = "{UnityEngine.AddressableAssets.Addressables.RuntimePath}\\StandaloneWindows64\\"
    bundle_key_map = {
        EN_ASSETS_BUNDLE_KEY: "localization-assets-spanish(es)_assets_all.bundle",
        EN_STRING_BUNDLE_KEY: "localization-string-tables-spanish(es)_assets_all.bundle",
        EN_ASSET_TABLES_BUNDLE_KEY: "localization-asset-tables-spanish(es)_assets_all.bundle",
    }
    mapper = make_es_string_mapper(bundle_map, bundle_key_map)

    new_buckets: list[Bucket] = [Bucket(b.key, b.key_raw, list(b.entry_indices)) for b in cat.buckets]
    new_locations: list[Location] = list(cat.locations)
    existing = {_key_fingerprint(b.key) for b in new_buckets}

    def append_location(loc: Location) -> int:
        new_locations.append(loc)
        return len(new_locations) - 1

    def add_bucket(key: Any, entry_indices: list[int], key_raw: Optional[bytes] = None) -> None:
        fp = _key_fingerprint(key)
        if fp in existing:
            return
        new_buckets.append(Bucket(key=key, key_raw=key_raw or encode_object_v1(key), entry_indices=entry_indices))
        existing.add(fp)

    # Clone en-keyed buckets (bundles, assets, tables, label Locale-en, …)
    for bucket in cat.buckets:
        if not bucket_is_en_clone_source(bucket, cat, mapper):
            continue
        new_key = _mapped_new_bucket_key(bucket.key, mapper)
        new_entry_indices: list[int] = []
        for ei in bucket.entry_indices:
            src = cat.locations[ei]
            extra = _prepare_extra(src, mapper, bundle_map, bundle_hashes, zero_crc_bundles)
            new_loc = src.copy_mapped(mapper, extra_data=extra, extra_data_raw=None)
            new_loc.primary_key = new_key
            new_idx = append_location(new_loc)
            new_entry_indices.append(new_idx)
        add_bucket(new_key, new_entry_indices)

    # Append Spanish locale to shared "Locale" label bucket
    for bucket in new_buckets:
        if bucket.key != "Locale":
            continue
        for ei in bucket.entry_indices:
            src = new_locations[ei]
            if src.internal_id != "Assets/Localize/English (en).asset":
                continue
            extra = _prepare_extra(src, mapper, bundle_map, bundle_hashes, zero_crc_bundles)
            es_loc = src.copy_mapped(mapper, extra_data=extra, extra_data_raw=None)
            es_loc.primary_key = "Spanish (es)"
            bucket.entry_indices.append(append_location(es_loc))
            break

    if zero_crc_bundles:
        for loc in new_locations:
            if isinstance(loc.extra_data, dict) and loc.extra_data.get("kind") == "AssetBundleRequestOptions":
                if any(
                    tok in loc.internal_id
                    for tok in ("english(en)", "spanish(es)", "localization-", "Assets/Localize/")
                ):
                    loc.extra_data = abro_set_crc_zero(loc.extra_data)
                    loc.extra_data_raw = None

    return Catalog(
        raw=copy.deepcopy(cat.raw),
        provider_ids=list(cat.provider_ids),
        internal_ids=list(cat.internal_ids),
        resource_types=list(cat.resource_types),
        internal_id_prefixes=list(cat.internal_id_prefixes),
        locations=new_locations,
        buckets=new_buckets,
        keys=[],
        _original_blobs=dict(cat._original_blobs),
        dirty=True,
    )


def _location_matches_hijack_en_bundle(loc: Location) -> bool:
    if loc.provider_id != BUNDLE_PROVIDER:
        return False
    return any(marker in loc.internal_id for marker in HIJACK_EN_BUNDLE_PATH_MARKERS)


def _abro_fingerprint(extra: Any) -> dict[str, Any] | None:
    if not isinstance(extra, dict) or extra.get("kind") != "AssetBundleRequestOptions":
        return None
    data = extra.get("data") or json.loads(extra["json_text"])
    return {
        "m_Crc": data.get("m_Crc"),
        "m_UseCrcForCachedBundles": data.get("m_UseCrcForCachedBundles"),
        "m_Hash": data.get("m_Hash"),
        "m_BundleName": data.get("m_BundleName"),
    }


def patch_crc_hijack_en_bundles(cat: Catalog) -> Catalog:
    """Disable CRC validation for the three English localization bundle locations."""
    new_locations: list[Location] = []
    patched_indices: list[int] = []
    for idx, loc in enumerate(cat.locations):
        loc_copy = Location(
            internal_id=loc.internal_id,
            provider_id=loc.provider_id,
            dependency_key=loc.dependency_key,
            extra_data=loc.extra_data,
            dependency_hash=loc.dependency_hash,
            primary_key=loc.primary_key,
            resource_type=loc.resource_type,
            extra_data_raw=loc.extra_data_raw,
            entry_index=loc.entry_index,
        )
        if _location_matches_hijack_en_bundle(loc):
            if not isinstance(loc.extra_data, dict) or loc.extra_data.get("kind") != "AssetBundleRequestOptions":
                raise ValueError(f"Expected ABRO on hijack bundle location: {loc.internal_id!r}")
            loc_copy.extra_data = abro_set_crc_zero(loc.extra_data)
            loc_copy.extra_data_raw = None
            patched_indices.append(idx)
        new_locations.append(loc_copy)

    if len(patched_indices) != len(HIJACK_EN_BUNDLE_PATH_MARKERS):
        raise ValueError(f"Expected to patch {len(HIJACK_EN_BUNDLE_PATH_MARKERS)} bundle locations, got {len(patched_indices)}: {patched_indices}")

    return Catalog(
        raw=copy.deepcopy(cat.raw),
        provider_ids=list(cat.provider_ids),
        internal_ids=list(cat.internal_ids),
        resource_types=list(cat.resource_types),
        internal_id_prefixes=list(cat.internal_id_prefixes),
        locations=new_locations,
        buckets=[Bucket(b.key, b.key_raw, list(b.entry_indices)) for b in cat.buckets],
        keys=[],
        _original_blobs=dict(cat._original_blobs),
        dirty=True,
    )


def diff_catalog_patch_crc(original: Catalog, patched: Catalog) -> dict[str, Any]:
    """Report locations whose ABRO fingerprint changed."""
    if len(original.locations) != len(patched.locations):
        raise ValueError("Location count mismatch")
    changed: list[dict[str, Any]] = []
    for i, (a, b) in enumerate(zip(original.locations, patched.locations)):
        fa, fb = _abro_fingerprint(a.extra_data), _abro_fingerprint(b.extra_data)
        if fa == fb:
            continue
        if a.internal_id != b.internal_id or a.provider_id != b.provider_id:
            raise ValueError(f"Non-ABRO drift at index {i}")
        changed.append({"index": i, "internal_id": a.internal_id, "before": fa, "after": fb})
    return {"changed_count": len(changed), "changed": changed}


def catalog_file_md5(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def collect_en_mirror_locations(cat: Catalog) -> list[dict]:
    """Catalog locations that clone-locale mirrors (en-related bucket keys)."""
    mapper = make_es_string_mapper()
    rows = []
    for b in cat.buckets:
        if not bucket_is_en_clone_source(b, cat, mapper):
            continue
        for ei in b.entry_indices:
            loc = cat.locations[ei]
            rows.append(
                {
                    "bucket_key": key_to_display(b.key),
                    "primary_key": key_to_display(loc.primary_key),
                    "internal_id": loc.internal_id,
                    "provider": loc.provider_id,
                    "dependency_key": None if loc.dependency_key is None else key_to_display(loc.dependency_key),
                    "resource_type": loc.resource_type.class_name if loc.resource_type else None,
                }
            )
    # Also the English entry under the Locale label bucket
    for b in cat.buckets:
        if b.key != "Locale":
            continue
        for ei in b.entry_indices:
            loc = cat.locations[ei]
            if loc.internal_id == "Assets/Localize/English (en).asset":
                rows.append(
                    {
                        "bucket_key": "Locale",
                        "primary_key": key_to_display(loc.primary_key),
                        "internal_id": loc.internal_id,
                        "provider": loc.provider_id,
                        "dependency_key": None if loc.dependency_key is None else key_to_display(loc.dependency_key),
                        "resource_type": loc.resource_type.class_name if loc.resource_type else None,
                    }
                )
    return rows
