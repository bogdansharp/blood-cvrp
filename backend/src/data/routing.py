from math import inf

from backend.src.data.interfaces import DistanceRepository, GeometryRepository, RoutingProvider


class RoutingData:
    '''
    Caching layer for routing data (distances, durations, geometries) that uses
    a RoutingProvider to fetch missing data and repositories to store it for future use.
    '''

    _ALLOWED_EDGE_FIELDS = {"distance", "duration"}


    def __init__(self, 
        dist_repo: DistanceRepository, 
        geom_repo: GeometryRepository,
        routing: RoutingProvider,
    ) -> None:
        self._dist_repo = dist_repo
        self._geom_repo = geom_repo
        self._routing = routing


    def get_edges(self, 
        src_lat_e6: int, src_lng_e6: int, dst: list[tuple[int, int]]
    ) -> list[tuple[float, float]]:
        if not dst:
            return []

        missed_idx = []
        result = [(inf, inf)] * len(dst)

        for i, (dst_lat_e6, dst_lng_e6) in enumerate(dst):
            if dst_lat_e6 == src_lat_e6 and dst_lng_e6 == src_lng_e6:
                result[i] = (0.0, 0.0)
                continue
            
            res = self._dist_repo.get(src_lat_e6, src_lng_e6, dst_lat_e6, dst_lng_e6)

            if res is None:
                missed_idx.append(i)
            else:
                result[i] = res

        if missed_idx:
            missing_dst = [dst[i] for i in missed_idx]

            try:
                edge_data = self._routing.get_distance_and_time(
                    src_lat_e6, src_lng_e6, missing_dst
                )
            except Exception as e:
                raise RuntimeError(f"Error occurred while fetching missing distances: {e}") from e

            if len(edge_data) != len(missing_dst):
                raise RuntimeError(
                    f"Routing provider returned invalid number of edges: "
                    f"expected={len(missing_dst)}, actual={len(edge_data)}"
                )

            for idx, (edge_dist, edge_time) in enumerate(edge_data):
                dst_idx = missed_idx[idx]

                if edge_dist is None or edge_time is None:
                    raise RuntimeError(
                        f"Routing provider returned empty edge data for destination index {dst_idx}"
                    )

                edge_dist = float(edge_dist)
                edge_time = float(edge_time)

                result[dst_idx] = (edge_dist, edge_time)

                self._dist_repo.update(
                    src_lat_e6=src_lat_e6,
                    src_lng_e6=src_lng_e6,
                    dst_lat_e6=dst[dst_idx][0],
                    dst_lng_e6=dst[dst_idx][1],
                    distance=edge_dist,
                    travel_time=edge_time,
                )

        if any(value == inf for value in result):
            raise RuntimeError("Some edge data is still missing after routing provider fetch")

        return result

    # def _get_edge_data(self, 
    #     src_lat_e6: int, src_lng_e6: int, dst: list[tuple[int, int]], data_field: str
    # ) -> list[float]:
    #     if data_field not in self._ALLOWED_EDGE_FIELDS:
    #         raise ValueError(f"Field '{data_field}' is not allowed")

    #     if not dst:
    #         return []

    #     missed_idx = []
    #     result = [inf] * len(dst)

    #     for i, (dst_lat_e6, dst_lng_e6) in enumerate(dst):
    #         res = self._dist_repo.get(src_lat_e6, src_lng_e6, dst_lat_e6, dst_lng_e6)

    #         if res is None:
    #             missed_idx.append(i)
    #         else:
    #             result[i] = float(res[0]) if data_field == "distance" else float(res[1])

    #     if missed_idx:
    #         missing_dst = [dst[i] for i in missed_idx]

    #         try:
    #             edge_data = self._routing.get_distance_and_time(
    #                 src_lat_e6, src_lng_e6, missing_dst
    #             )
    #         except Exception as e:
    #             raise RuntimeError(f"Error occurred while fetching missing distances: {e}") from e

    #         if len(edge_data) != len(missing_dst):
    #             raise RuntimeError(
    #                 f"Routing provider returned invalid number of edges: "
    #                 f"expected={len(missing_dst)}, actual={len(edge_data)}"
    #             )

    #         for idx, (edge_dist, edge_time) in enumerate(edge_data):
    #             dst_idx = missed_idx[idx]

    #             if edge_dist is None or edge_time is None:
    #                 raise RuntimeError(
    #                     f"Routing provider returned empty edge data for destination index {dst_idx}"
    #                 )

    #             edge_dist = float(edge_dist)
    #             edge_time = float(edge_time)

    #             result[dst_idx] = edge_dist if data_field == "distance" else edge_time

    #             self._dist_repo.update(
    #                 src_lat_e6=src_lat_e6,
    #                 src_lng_e6=src_lng_e6,
    #                 dst_lat_e6=dst[dst_idx][0],
    #                 dst_lng_e6=dst[dst_idx][1],
    #                 distance=edge_dist,
    #                 travel_time=edge_time,
    #             )

    #     if any(value == inf for value in result):
    #         raise RuntimeError("Some edge data is still missing after routing provider fetch")

    #     return result
    

    def get_distance(self, 
        src_lat_e6: int, src_lng_e6: int, dst: list[tuple[int, int]]
    ) -> list[float]:
        edges = self.get_edges(src_lat_e6, src_lng_e6, dst)
        return [edge[0] for edge in edges]
        

    def get_duration(self, 
        src_lat_e6: int, src_lng_e6: int, dst: list[tuple[int, int]]
    ) -> list[float]:
        edges = self.get_edges(src_lat_e6, src_lng_e6, dst)
        return [edge[1] for edge in edges]


    def get_geometry(self,
        src_lat_e6: int, src_lng_e6: int, dst_lat_e6: int, dst_lng_e6: int
    ) -> list[tuple[int, int]]:
        geometry = self._geom_repo.get(src_lat_e6, src_lng_e6, dst_lat_e6, dst_lng_e6)

        if geometry is not None:
            if not geometry:
                raise RuntimeError("Cached geometry is empty")
            return geometry

        try:
            geometry = self._routing.get_geometry(
                src_lat_e6, src_lng_e6, dst_lat_e6, dst_lng_e6
            )
        except Exception as e:
            raise RuntimeError(f"Error occurred while fetching geometry: {e}") from e

        if not geometry:
            raise RuntimeError("Routing provider returned empty geometry")

        self._geom_repo.update(
            src_lat_e6=src_lat_e6,
            src_lng_e6=src_lng_e6,
            dst_lat_e6=dst_lat_e6,
            dst_lng_e6=dst_lng_e6,
            geometry=geometry,
        )

        return geometry
    

    def get_snap_location(self, lat_e6: int, lng_e6: int) -> tuple[int, int, float]:
        return self._routing.get_snap_location(lat_e6, lng_e6)