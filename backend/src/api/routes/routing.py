from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from backend.src.application.routing import RoutingService, get_routing_service

router = APIRouter(prefix="/routing", tags=["routing"])


@router.get("/geometry", responses={
    400: {"description": "Invalid request"},
    502: {"description": "Error fetching geometry"},
})
async def get_geometry(
    src_lat_e6: int, src_lng_e6: int, dst_lat_e6: int, dst_lng_e6: int,
    routing_service: Annotated[RoutingService, Depends(get_routing_service)],
) -> list[tuple[float, float]]:
    try:
        geometry_e6 = routing_service.get_geometry(
            src_lat_e6=src_lat_e6,
            src_lng_e6=src_lng_e6,
            dst_lat_e6=dst_lat_e6,
            dst_lng_e6=dst_lng_e6
        )
        geometry = [(lat_e6 / 1e6, lng_e6 / 1e6) for lat_e6, lng_e6 in geometry_e6]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return geometry

@router.get("/snap", responses={
    400: {"description": "Invalid request"},
    502: {"description": "Error fetching snap location"},
})
async def get_snap_location(
    lat_e6: int, lng_e6: int,
    routing_service: Annotated[RoutingService, Depends(get_routing_service)],
) -> tuple[int, int, float]:
    try:
        snap_location = routing_service.get_snap_location(
            lat_e6=lat_e6,
            lng_e6=lng_e6
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return snap_location
