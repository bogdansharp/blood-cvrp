from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.src.api.models import Hospital
from backend.src.application.hospitals import HospitalService, get_hospital_service

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


@router.get("/{hospital_id}", responses={404: {"description": "Hospital not found"}})
async def get_hospital(
    hospital_id: int,
    hospital_service: Annotated[HospitalService, Depends(get_hospital_service)],
) -> Hospital:
    hospital = hospital_service.get_hospital(hospital_id)
    if hospital is None:
        raise HTTPException(status_code=404)
    return hospital


@router.get("/", response_model=list[Hospital])
async def list_hospitals(
    hospital_service: Annotated[HospitalService, Depends(get_hospital_service)]
):
    hospitals = hospital_service.list_hospitals()
    return hospitals


@router.delete("/{hospital_id}", status_code=204, responses={404: {"description": "Hospital not found"}})
async def delete_hospital(
    hospital_id: int,
    hospital_service: Annotated[HospitalService, Depends(get_hospital_service)],
) -> None:
    is_deleted = hospital_service.delete_hospital(hospital_id)
    if not is_deleted:
        raise HTTPException(status_code=404)