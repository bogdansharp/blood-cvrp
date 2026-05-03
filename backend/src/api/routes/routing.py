from fastapi import APIRouter, Depends, HTTPException
from backend.src.application.routing import RoutingService, get_routing_service

router = APIRouter(prefix="/routing", tags=["routing"])


@router.get("/geometry")
async def get_geometry(
    src_lat_e6: int, src_lng_e6: int, dst_lat_e6: int, dst_lng_e6: int,
    routing_service: RoutingService = Depends(get_routing_service),
) -> list[tuple[int, int]]:
    try:
        geometry = routing_service.get_geometry(
            src_lat_e6=src_lat_e6,
            src_lng_e6=src_lng_e6,
            dst_lat_e6=dst_lat_e6,
            dst_lng_e6=dst_lng_e6
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return geometry

@router.get("/snap")
async def get_snap_location(
    lat_e6: int, lng_e6: int,
    routing_service: RoutingService = Depends(get_routing_service),
) -> tuple[int, int, float]:
    try:
        snap_location = routing_service.get_snap_location(
            lat_e6=lat_e6,
            lng_e6=lng_e6
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return snap_location
