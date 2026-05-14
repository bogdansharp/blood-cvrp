import pytest

from backend.src.data.routing_provider import ORSRoutingProvider


class FakeResponse:
    def __init__(self, status_code: int, data: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._data = data or {}
        self.text = text

    def json(self) -> dict:
        return self._data


class FakePost:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    def __call__(self, url, headers, json, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return self.responses.pop(0)


def make_provider(fake_post: FakePost) -> ORSRoutingProvider:
    return ORSRoutingProvider(
        ors_api_key="dummy",
        ors_base_url="https://atu.ie",
        ors_profile="driving-car",
        call_timeout_sec=5,
        http_post=fake_post,
    )


def test_matrix_request_returns_distance_and_duration() -> None:
    fake_post = FakePost([
        FakeResponse(
            200,
            {
                "distances": [[100.5, 200.5]],
                "durations": [[10.0, 20.0]],
            },
        )
    ])
    provider = make_provider(fake_post)

    result = provider.get_distance_and_time(53100000, -8200000, [(53200000, -8300000), (53300000, -8400000)])

    assert result == [(100.5, 10.0), (200.5, 20.0)]

    call = fake_post.calls[0]
    assert call["url"] == "https://atu.ie/v2/matrix/driving-car"
    assert call["headers"]["Authorization"] == "dummy"
    assert call["timeout"] == 5
    assert call["json"]["locations"] == [
        [-8.2, 53.1],
        [-8.3, 53.2],
        [-8.4, 53.3],
    ]
    assert call["json"]["sources"] == [0]
    assert call["json"]["destinations"] == [1, 2]


def test_matrix_empty_destinations_returns_empty_without_http_call() -> None:
    fake_post = FakePost([])
    provider = make_provider(fake_post)

    assert provider.get_distance_and_time(53100000, -8200000, []) == []
    assert fake_post.calls == []


def test_matrix_non_200_raises() -> None:
    fake_post = FakePost([FakeResponse(500, text="server error")])
    provider = make_provider(fake_post)

    with pytest.raises(RuntimeError):
        provider.get_distance_and_time(53100000, -8200000, [(53200000, -8300000)])


def test_matrix_malformed_response_raises() -> None:
    fake_post = FakePost([FakeResponse(200, {"distances": [[100.0]]})])
    provider = make_provider(fake_post)

    with pytest.raises(RuntimeError):
        provider.get_distance_and_time(53100000, -8200000, [(53200000, -8300000)])


def test_geometry_request_parses_geojson_coordinates_to_e6() -> None:
    fake_post = FakePost([
        FakeResponse(
            200,
            {
                "features": [
                    {
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [
                                [-8.2, 53.1],
                                [-8.25, 53.15],
                                [-8.3, 53.2],
                            ],
                        }
                    }
                ]
            },
        )
    ])
    provider = make_provider(fake_post)

    result = provider.get_geometry(53100000, -8200000, 53200000, -8300000)

    assert result == [
        (53100000, -8200000),
        (53150000, -8250000),
        (53200000, -8300000),
    ]

    call = fake_post.calls[0]
    assert call["url"] == "https://atu.ie/v2/directions/driving-car/geojson"
    assert call["json"]["coordinates"] == [[-8.2, 53.1], [-8.3, 53.2]]
    assert call["json"]["geometry"] is True
    assert call["json"]["instructions"] is False


def test_geometry_429_sets_cooldown_and_next_request_skips_http() -> None:
    fake_post = FakePost([FakeResponse(429, text="rate limited")])
    provider = make_provider(fake_post)

    with pytest.raises(RuntimeError):
        provider.get_geometry(53100000, -8200000, 53200000, -8300000)

    with pytest.raises(RuntimeError):
        provider.get_geometry(53100000, -8200000, 53200000, -8300000)

    assert len(fake_post.calls) == 1


def test_geometry_malformed_response_raises() -> None:
    fake_post = FakePost([FakeResponse(200, {"features": []})])
    provider = make_provider(fake_post)

    with pytest.raises(RuntimeError):
        provider.get_geometry(53100000, -8200000, 53200000, -8300000)


def test_snap_request_parses_location() -> None:
    fake_post = FakePost([
        FakeResponse(
            200,
            {
                "locations": [
                    {
                        "location": [-8.200001, 53.100001],
                        "snapped_distance": 12.5,
                    }
                ]
            },
        )
    ])
    provider = make_provider(fake_post)

    result = provider.get_snap_location(53100000, -8200000)

    assert result == (53100001, -8200001, 12.5)

    call = fake_post.calls[0]
    assert call["url"] == "https://atu.ie/v2/snap/driving-car"
    assert call["json"]["locations"] == [[-8.2, 53.1]]
    assert call["json"]["radius"] == 350


def test_snap_malformed_response_raises() -> None:
    fake_post = FakePost([FakeResponse(200, {"locations": []})])
    provider = make_provider(fake_post)

    with pytest.raises(RuntimeError):
        provider.get_snap_location(53100000, -8200000)