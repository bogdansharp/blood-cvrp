import json
from pathlib import Path

from backend.src.data.interfaces import GeometryRepository


class JSONGeometryRepository(GeometryRepository):
    """JSON implementation of GeometryRepository."""

    _SUB_DIR_NAME = "geometries"


    def __init__(self, storage_root: str | Path) -> None:
        storage_root_path = Path(storage_root)
        self._dir = storage_root_path / self._SUB_DIR_NAME
        self._dir.mkdir(parents=True, exist_ok=True)


    def _path_for(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst_lat_e6: int,
        dst_lng_e6: int,
    ) -> Path:
        name = f"{src_lat_e6}_{src_lng_e6}_{dst_lat_e6}_{dst_lng_e6}.json"
        return self._dir / name


    def get(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst_lat_e6: int,
        dst_lng_e6: int,
    ) -> list[tuple[int, int]] | None:
        geometry_path = self._path_for(src_lat_e6, src_lng_e6, dst_lat_e6, dst_lng_e6)
        if not geometry_path.exists():
            return None
        try:
            data = json.loads(geometry_path.read_text(encoding="utf-8"))
            points = data["geometry"]
            return [tuple(point) for point in points]
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None


    def update(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst_lat_e6: int,
        dst_lng_e6: int,
        geometry: list[tuple[int, int]],
    ) -> bool:
        geometry_path = self._path_for(src_lat_e6, src_lng_e6, dst_lat_e6, dst_lng_e6)
        payload = {"geometry": geometry}
        try:
            geometry_path.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
            return True
        except OSError:
            return False


    def delete(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst_lat_e6: int,
        dst_lng_e6: int,
    ) -> bool:
        geometry_path = self._path_for(src_lat_e6, src_lng_e6, dst_lat_e6, dst_lng_e6)
        if not geometry_path.exists():
            return False
        try:
            geometry_path.unlink()
            return True
        except OSError:
            return False
