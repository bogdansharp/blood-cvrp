import requests

from backend.src.data.interfaces import RoutingProvider


class ORSRoutingProvider(RoutingProvider):
    '''
    Routing provider implementation using external OpenRouteService API.
    '''

    _PROFILE = "driving-car"
    _MATRIX_ENDPOINT = f"/v2/matrix/{_PROFILE}"
    _SNAP_ENDPOINT = f"/v2/snap/{_PROFILE}"
    _GEOMETRY_ENDPOINT = f"/v2/directions/{_PROFILE}/geojson"

    def __init__(self, 
        ors_api_key: str, 
        ors_base_url: str,
        call_timeout_sec: int = 30, 
        max_snap_dist: int = 500,
        simplify_geometry: bool = False,
    ) -> None:
        ors_base_url = ors_base_url.rstrip("/")

        self._ors_api_key = ors_api_key
        self._call_timeout_sec = call_timeout_sec
        self._matrix_url = ors_base_url + self._MATRIX_ENDPOINT
        self._snap_url = ors_base_url + self._SNAP_ENDPOINT
        self._geometry_url = ors_base_url + self._GEOMETRY_ENDPOINT
        self._max_snap_dist = max_snap_dist
        self._simplify_geometry = simplify_geometry


    def get_geometry(self, 
        src_lat_e6: int, src_lng_e6: int, dst_lat_e6: int, dst_lng_e6: int
    ) -> list[tuple[int, int]]:
        coordinates = [
            [src_lng_e6 / 1e6, src_lat_e6 / 1e6],
            [dst_lng_e6 / 1e6, dst_lat_e6 / 1e6],
        ]
        headers = {
            "Authorization": self._ors_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "coordinates":            coordinates,
            "elevation":               False,
            "geometry":                True,
            "geometry_simplify":       self._simplify_geometry,
            "instructions":            False,
            "units":                   "m",        # distance in metres
        }
        response = requests.post(
            self._geometry_url, 
            headers=headers, 
            json=payload, 
            timeout=self._call_timeout_sec
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Geometry request failed: "
                f"{response.status_code} {response.text}"
            )

        data = response.json()

        if "features" not in data:
            raise RuntimeError(f"Unexpected API response: {data}")

        features = data["features"]
        if not features or len(features) < 1:
            raise RuntimeError("Unexpected API response format: features is empty")

        feature = features[0]
        if "geometry" not in feature:
            raise RuntimeError("Unexpected API response format: geometry is missing")

        geometry = feature["geometry"]
        if not geometry:
            raise RuntimeError("Unexpected API response format: geometry is empty")

        if geometry.get("type") != "LineString":
            raise RuntimeError(f"Unexpected API response format: geometry type is {geometry.get('type')}")

        if "coordinates" not in geometry:
            raise RuntimeError("Unexpected API response format: coordinates are missing")

        route_coordinates = geometry["coordinates"]
        if not route_coordinates:
            raise RuntimeError("Unexpected API response format: coordinates are empty")

        result: list[tuple[int, int]] = []
        for coordinate in route_coordinates:
            if not coordinate or len(coordinate) < 2:
                raise RuntimeError(f"Unexpected coordinate format: {coordinate}")

            lng = coordinate[0]
            lat = coordinate[1]

            lat_e6 = int(round(lat * 1e6))
            lng_e6 = int(round(lng * 1e6))

            result.append((lat_e6, lng_e6))

        return result


    def get_distance_and_time(self, 
        src_lat_e6: int, src_lng_e6: int, dst: list[tuple[int, int]]
    ) -> list[tuple[float, float]]:
        if not dst:
            return []

        locations = [[src_lng_e6 / 1e6, src_lat_e6 / 1e6]]
        for dst_lat_e6, dst_lng_e6 in dst:
            locations.append([dst_lng_e6 / 1e6, dst_lat_e6 / 1e6])

        src_idxs, dst_idxs = [0], list(range(1, len(locations)))
        headers = {
            "Authorization": self._ors_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "locations":            locations,
            "destinations":         dst_idxs,
            "metrics":              ["distance", "duration"],
            "units":                "m",        # distance in metres
            "resolve_locations":    False,
            "sources":              src_idxs,
        }
        response = requests.post(
            self._matrix_url, 
            headers=headers, 
            json=payload, 
            timeout=self._call_timeout_sec
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Matrix request failed: "
                f"{response.status_code} {response.text}"
            )

        data = response.json()

        if "distances" not in data or "durations" not in data:
            raise RuntimeError(f"Unexpected API response: {data}")

        distances = data["distances"]
        durations = data["durations"]

        if not distances or not durations or len(distances) != 1 or len(durations) != 1:
            raise RuntimeError(f"Unexpected API response format: {data}")

        if len(distances[0]) != len(dst) or len(durations[0]) != len(dst):
            raise RuntimeError(
                f"API response size mismatch: "
                f"len(distances)={len(distances[0])}, "
                f"len(durations)={len(durations[0])}"
            )

        result: list[tuple[float, float]] = []
        for distance, duration in zip(distances[0], durations[0]):
            if distance is None or duration is None:
                raise RuntimeError(f"Route is unreachable according to ORS matrix response: {data}")

            result.append((float(distance), float(duration)))

        return result
    

    def get_snap_location(self, 
        lat_e6: int, lng_e6: int
    ) -> tuple[int, int, float]:
        locations = [[lng_e6 / 1e6, lat_e6 / 1e6]]
        headers = {
            "Authorization": self._ors_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "locations":            locations,
            "radius":               self._max_snap_dist,
        }
        response = requests.post(
            self._snap_url, 
            headers=headers, 
            json=payload, 
            timeout=self._call_timeout_sec
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Snap request failed: "
                f"{response.status_code} {response.text}"
            )

        data = response.json()

        if "locations" not in data:
            raise RuntimeError(f"Unexpected API response: {data}")

        locations = data["locations"]
        if not locations or len(locations) != 1:
            raise RuntimeError(f"Unexpected API response format: {data}")

        snap_location = locations[0]
        if (
            not snap_location
            or "location" not in snap_location
            or len(snap_location["location"]) != 2
            or "snapped_distance" not in snap_location
        ):  
            raise RuntimeError(f"Unexpected API response format: {data}")

        snap_lng = int(round(snap_location["location"][0] * 1e6))
        snap_lat = int(round(snap_location["location"][1] * 1e6))
        snap_dist = float(snap_location["snapped_distance"])

        return (snap_lat, snap_lng, snap_dist)