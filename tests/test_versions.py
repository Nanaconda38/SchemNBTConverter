from schem_nbt_converter.versions import parse_versions


def test_parse_versions_joins_mojang_manifest_and_data_versions() -> None:
    manifest = {
        "versions": [
            {"id": "26.2", "type": "release"},
            {"id": "unknown", "type": "snapshot"},
        ]
    }
    data_versions = {
        "value": [
            {"minecraftVersion": "26.2", "dataVersion": 4903},
            {"minecraftVersion": "unknown", "dataVersion": "invalid"},
        ]
    }

    assert parse_versions(manifest, data_versions) == [("26.2", "release", 4903)]
