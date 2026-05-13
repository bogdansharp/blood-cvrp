from backend.src.models import Hospital
from fastapi import Depends

from backend.src.application.dependencies import get_hospital_repository
from backend.src.data.interfaces import HospitalRepository


class HospitalService:
    def __init__(self, repo: HospitalRepository) -> None:
        self._repo = repo

    def list_hospitals(self) -> list[Hospital]:
        return self._repo.get_all()
    
    def get_hospital(self, id: int) -> Hospital | None:
        return self._repo.get(id)

    def delete_hospital(self, id: int) -> bool:
        return self._repo.delete(id)


def get_hospital_service(
    repo: HospitalRepository = Depends(get_hospital_repository),
) -> HospitalService:
    return HospitalService(repo)