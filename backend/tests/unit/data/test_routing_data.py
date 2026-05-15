import logging
from typing import Any

import pytest

from backend.src.data.routing import RoutingData


class FakeDistanceRepo:
    def __init__(
        self,
        cached: list[tuple[int, int, float, float]] | None = None,
        update_result: bool = True,
    ) -> None:
        self.cached = cached
        self.update_result = update_result
        self.get_calls: list[tuple[int, int, list[tuple[int, int]]]] = []
        self.update_calls: list[
            tuple[int, int, list[tuple[int, int, float, float]]]
        ] = []

    def get(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst: list[tuple[int, int]],
    ) -> list[tuple[int, int, float, float]] | None:
        self.get_calls.append((src_lat_e6, src_lng_e6, dst))
        return self.cached

    def update(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst: list[tuple[int, int, float, float]],
    ) -> bool:
        self.update_calls.append((src_lat_e6, src_lng_e6, dst))
        return self.update_result

    def delete(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst_lat_e6: int,
        dst_lng_e6: int,
    ) -> bool:
        return True


class FakeGeometryRepo:
    def __init__(
        self,
        cached: list[tuple[int, int]] | None = None,
        update_result: bool = True,
    ) -> None:
        self.cached = cached
        self.update_result = update_result
        self.get_calls: list[tuple[int, int, int, int]] = []
        self.update_calls: list[tuple[int, int, int, int, list[tuple[int, int]]]] = []

    def get(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst_lat_e6: int,
        dst_lng_e6: int,
    ) -> list[tuple[int, int]] | None:
        self.get_calls.append((src_lat_e6, src_lng_e6, dst_lat_e6, dst_lng_e6))
        return self.cached

    def update(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst_lat_e6: int,
        dst_lng_e6: int,
        geometry: list[tuple[int, int]],
    ) -> bool:
        self.update_calls.append(
            (src_lat_e6, src_lng_e6, dst_lat_e6, dst_lng_e6, geometry)
        )
        return self.update_result

    def delete(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst_lat_e6: int,
        dst_lng_e6: int,
    ) -> bool:
        return True


class FakeRoutingProvider:
    def __init__(
        self,
        edges: list[tuple[Any, Any]] | None = None,
        geometry: list[tuple[int, int]] | None = None,
        edge_error: Exception | None = None,
        geometry_error: Exception | None = None,
    ) -> None:
        self.edges: list[tuple[Any, Any]] = edges or []
        self.geometry = geometry or []
        self.edge_error = edge_error
        self.geometry_error = geometry_error
        self.edge_calls: list[tuple[int, int, list[tuple[int, int]]]] = []
        self.geometry_calls: list[tuple[int, int, int, int]] = []

    def get_distance_and_time(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst: list[tuple[int, int]],
    ) -> list[tuple[float, float]]:
        self.edge_calls.append((src_lat_e6, src_lng_e6, dst))
        if self.edge_error is not None:
            raise self.edge_error
        return self.edges

    def get_geometry(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst_lat_e6: int,
        dst_lng_e6: int,
    ) -> list[tuple[int, int]]:
        self.geometry_calls.append((src_lat_e6, src_lng_e6, dst_lat_e6, dst_lng_e6))
        if self.geometry_error is not None:
            raise self.geometry_error
        return self.geometry

    def get_snap_location(self, lat_e6: int, lng_e6: int) -> tuple[int, int, float]:
        return (lat_e6 + 1, lng_e6 + 1, 12.5)


def test_edges_cache_hit_skips_provider() -> None:
    dist_repo = FakeDistanceRepo(cached=[(2, 2, 100.0, 10.0)])
    geom_repo = FakeGeometryRepo()
    provider = FakeRoutingProvider()
    routing = RoutingData(dist_repo, geom_repo, provider)

    result = routing.get_edges(1, 1, [(2, 2)])

    assert result == [(100.0, 10.0)]
    assert provider.edge_calls == []
    assert dist_repo.update_calls == []


def test_edges_partial_cache_miss_fetches_only_missing() -> None:
    dist_repo = FakeDistanceRepo(cached=[(2, 2, 100.0, 10.0)])
    geom_repo = FakeGeometryRepo()
    provider = FakeRoutingProvider(edges=[(200.0, 20.0)])
    routing = RoutingData(dist_repo, geom_repo, provider)

    result = routing.get_edges(1, 1, [(2, 2), (3, 3)])

    assert result == [(100.0, 10.0), (200.0, 20.0)]
    assert provider.edge_calls == [(1, 1, [(3, 3)])]
    assert dist_repo.update_calls == [(1, 1, [(3, 3, 200.0, 20.0)])]


def test_edges_self_edge_is_zero() -> None:
    dist_repo = FakeDistanceRepo()
    geom_repo = FakeGeometryRepo()
    provider = FakeRoutingProvider()
    routing = RoutingData(dist_repo, geom_repo, provider)

    result = routing.get_edges(1, 1, [(1, 1)])

    assert result == [(0.0, 0.0)]
    assert provider.edge_calls == []


def test_edges_provider_size_mismatch_raises() -> None:
    dist_repo = FakeDistanceRepo()
    geom_repo = FakeGeometryRepo()
    provider = FakeRoutingProvider(edges=[(100.0, 10.0)])
    routing = RoutingData(dist_repo, geom_repo, provider)

    with pytest.raises(RuntimeError):
        routing.get_edges(1, 1, [(2, 2), (3, 3)])


def test_edges_provider_empty_edge_raises() -> None:
    dist_repo = FakeDistanceRepo()
    geom_repo = FakeGeometryRepo()
    provider = FakeRoutingProvider(edges=[(None, 10.0)])
    routing = RoutingData(dist_repo, geom_repo, provider)

    with pytest.raises(RuntimeError):
        routing.get_edges(1, 1, [(2, 2)])


def test_edges_update_failure_logs_warning_but_returns_result(
    caplog: pytest.LogCaptureFixture,
) -> None:
    dist_repo = FakeDistanceRepo(update_result=False)
    geom_repo = FakeGeometryRepo()
    provider = FakeRoutingProvider(edges=[(100.0, 10.0)])
    routing = RoutingData(dist_repo, geom_repo, provider)

    with caplog.at_level(logging.WARNING):
        result = routing.get_edges(1, 1, [(2, 2)])

    assert result == [(100.0, 10.0)]
    assert "Failed to update distance repository" in caplog.text


def test_distance_and_duration_use_edges() -> None:
    dist_repo = FakeDistanceRepo(cached=[(2, 2, 100.0, 10.0)])
    geom_repo = FakeGeometryRepo()
    provider = FakeRoutingProvider()
    routing = RoutingData(dist_repo, geom_repo, provider)

    assert routing.get_distance(1, 1, [(2, 2)]) == [100.0]
    assert routing.get_duration(1, 1, [(2, 2)]) == [10.0]


def test_geometry_cache_hit_skips_provider() -> None:
    cached_geometry = [(1, 1), (2, 2)]
    dist_repo = FakeDistanceRepo()
    geom_repo = FakeGeometryRepo(cached=cached_geometry)
    provider = FakeRoutingProvider()
    routing = RoutingData(dist_repo, geom_repo, provider)

    result = routing.get_geometry(1, 1, 2, 2)

    assert result == cached_geometry
    assert provider.geometry_calls == []


def test_geometry_missing_fetches_provider_and_updates_cache() -> None:
    geometry = [(1, 1), (2, 2)]
    dist_repo = FakeDistanceRepo()
    geom_repo = FakeGeometryRepo()
    provider = FakeRoutingProvider(geometry=geometry)
    routing = RoutingData(dist_repo, geom_repo, provider)

    result = routing.get_geometry(1, 1, 2, 2)

    assert result == geometry
    assert provider.geometry_calls == [(1, 1, 2, 2)]
    assert geom_repo.update_calls == [(1, 1, 2, 2, geometry)]


def test_empty_cached_geometry_raises() -> None:
    dist_repo = FakeDistanceRepo()
    geom_repo = FakeGeometryRepo(cached=[])
    provider = FakeRoutingProvider()
    routing = RoutingData(dist_repo, geom_repo, provider)

    with pytest.raises(RuntimeError):
        routing.get_geometry(1, 1, 2, 2)


def test_provider_empty_geometry_raises() -> None:
    dist_repo = FakeDistanceRepo()
    geom_repo = FakeGeometryRepo()
    provider = FakeRoutingProvider(geometry=[])
    routing = RoutingData(dist_repo, geom_repo, provider)

    with pytest.raises(RuntimeError):
        routing.get_geometry(1, 1, 2, 2)


def test_geometry_update_failure_logs_warning_but_returns_geometry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    geometry = [(1, 1), (2, 2)]
    dist_repo = FakeDistanceRepo()
    geom_repo = FakeGeometryRepo(update_result=False)
    provider = FakeRoutingProvider(geometry=geometry)
    routing = RoutingData(dist_repo, geom_repo, provider)

    with caplog.at_level(logging.WARNING):
        result = routing.get_geometry(1, 1, 2, 2)

    assert result == geometry
    assert "Failed to update geometry repository" in caplog.text


def test_snap_location_delegates_to_provider() -> None:
    routing = RoutingData(
        FakeDistanceRepo(),
        FakeGeometryRepo(),
        FakeRoutingProvider(),
    )

    assert routing.get_snap_location(10, 20) == (11, 21, 12.5)
