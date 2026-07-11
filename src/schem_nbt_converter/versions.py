from __future__ import annotations

import json
from collections.abc import Mapping
from urllib.request import Request, urlopen

MOJANG_VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
DATA_VERSION_URL = (
    "https://raw.githubusercontent.com/PrismarineJS/minecraft-data/"
    "master/data/pc/common/protocolVersions.json"
)
MinecraftVersion = tuple[str, str, int]


def parse_versions(
    manifest: Mapping[str, object],
    data_versions: Mapping[str, object] | list[object],
) -> list[MinecraftVersion]:
    mapped_versions: dict[str, int] = {}
    entries = data_versions.get("value", []) if isinstance(data_versions, Mapping) else data_versions
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        version = entry.get("minecraftVersion")
        data_version = entry.get("dataVersion")
        if isinstance(version, str) and isinstance(data_version, int):
            mapped_versions[version] = data_version

    versions: list[MinecraftVersion] = []
    for entry in manifest.get("versions", []):
        if not isinstance(entry, Mapping):
            continue
        version = entry.get("id")
        if isinstance(version, str) and version in mapped_versions:
            versions.append((version, str(entry.get("type", "unknown")), mapped_versions[version]))
    if not versions:
        raise ValueError("No Minecraft versions with DataVersion were found.")
    return versions


def _load_json(url: str, timeout: float) -> object:
    request = Request(url, headers={"User-Agent": "SchemNBTConverter/1.3"})
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    return payload


def fetch_versions(timeout: float = 5.0) -> list[MinecraftVersion]:
    manifest = _load_json(MOJANG_VERSION_MANIFEST_URL, timeout)
    data_versions = _load_json(DATA_VERSION_URL, timeout)
    if not isinstance(manifest, Mapping):
        raise ValueError("Invalid Minecraft version manifest.")
    return parse_versions(
        manifest,
        data_versions if isinstance(data_versions, (Mapping, list)) else [],
    )
