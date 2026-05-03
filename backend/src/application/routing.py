

from fastapi import Depends

from backend.src.application.dependencies import get_routing_data
from backend.src.data.routing import RoutingData


class RoutingService:
    def __init__(self, routing_data: RoutingData) -> None:
        self._routing_data = routing_data

    def get_geometry(self, 
        src_lat_e6: int, src_lng_e6: int, dst_lat_e6: int, dst_lng_e6: int
    ) -> list[tuple[int, int]]:
        return self._routing_data.get_geometry(src_lat_e6, src_lng_e6, dst_lat_e6, dst_lng_e6)
    
    def get_snap_location(self, lat_e6: int, lng_e6: int) -> tuple[int, int, float]:
        return self._routing_data.get_snap_location(lat_e6, lng_e6)


def get_routing_service(
    routing_data: RoutingData = Depends(get_routing_data),
) -> RoutingService:
    return RoutingService(routing_data)