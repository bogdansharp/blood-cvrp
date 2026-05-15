import json
from pathlib import Path

from backend.src.data.interfaces import DistanceRepository


class JSONDistanceRepository(DistanceRepository):
    """JSON implementation of DistanceRepository."""

    _SUB_DIR_NAME = "distances"

    def __init__(self, storage_root: str | Path) -> None:
        storage_root_path = Path(storage_root)
        self._dir = storage_root_path / self._SUB_DIR_NAME
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, src_lat_e6: int, src_lng_e6: int) -> Path:
        name = f"{src_lat_e6}_{src_lng_e6}.json"
        return self._dir / name

    def _get_src_edges(
        self, src_lat_e6: int, src_lng_e6: int
    ) -> list[tuple[int, int, float, float]]:
        distance_path = self._path_for(src_lat_e6, src_lng_e6)
        if not distance_path.exists():
            return []
        try:
            data = json.loads(distance_path.read_text(encoding="utf-8"))
            return [
                (
                    int(item["dst_lat_e6"]),
                    int(item["dst_lng_e6"]),
                    float(item["distance"]),
                    float(item["travel_time"]),
                )
                for item in data.get("edges", [])
            ]
        except (OSError, KeyError, TypeError, ValueError):
            return []

    def _save_src_edges(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        edges: list[tuple[int, int, float, float]],
    ) -> bool:
        distance_path = self._path_for(src_lat_e6, src_lng_e6)
        edges_payload = []
        for dst_lat_e6, dst_lng_e6, distance, travel_time in edges:
            edges_payload.append(
                {
                    "dst_lat_e6": dst_lat_e6,
                    "dst_lng_e6": dst_lng_e6,
                    "distance": distance,
                    "travel_time": travel_time,
                }
            )
        payload = {"edges": edges_payload}
        try:
            distance_path.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
            return True
        except OSError:
            return False

    def get(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst: list[tuple[int, int]],
    ) -> list[tuple[int, int, float, float]] | None:
        all_edges = self._get_src_edges(src_lat_e6, src_lng_e6)
        if not all_edges:
            return None
        dst_set = {(dst_lat_e6, dst_lng_e6) for dst_lat_e6, dst_lng_e6 in dst}
        result = []
        for edge in all_edges:
            if (edge[0], edge[1]) in dst_set:
                result.append(edge)
        return result

    def update(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst: list[tuple[int, int, float, float]],
    ) -> bool:
        all_edges = self._get_src_edges(src_lat_e6, src_lng_e6)
        unique_edges = {(edge[0], edge[1]): edge for edge in all_edges}
        is_changed = False
        for edge in dst:
            dst_lat_e6, dst_lng_e6, dist, time = edge
            existing_edge = unique_edges.get((dst_lat_e6, dst_lng_e6))
            if (
                existing_edge is None
                or dist != existing_edge[2]
                or time != existing_edge[3]
            ):
                unique_edges[(dst_lat_e6, dst_lng_e6)] = edge
                is_changed = True

        if is_changed:
            return self._save_src_edges(
                src_lat_e6, src_lng_e6, list(unique_edges.values())
            )
        return True

    def delete(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst_lat_e6: int,
        dst_lng_e6: int,
    ) -> bool:
        all_edges = self._get_src_edges(src_lat_e6, src_lng_e6)
        remaining_edges = [
            edge
            for edge in all_edges
            if not (edge[0] == dst_lat_e6 and edge[1] == dst_lng_e6)
        ]
        if len(remaining_edges) == len(all_edges):
            return False

        return self._save_src_edges(src_lat_e6, src_lng_e6, remaining_edges)
