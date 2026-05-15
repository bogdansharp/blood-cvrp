from typing import Protocol

from backend.src.models import (
    Hospital,
    LogEntry,
    Scenario,
    ScenarioReduced,
    Solution,
    SolverJob,
)


class ScenarioRepository(Protocol):
    def create(self, scenario: Scenario) -> Scenario | None: ...

    def get(self, scenario_id: int) -> Scenario | None: ...

    def get_all(self) -> list[ScenarioReduced]: ...

    def update(self, scenario: Scenario) -> Scenario | None: ...

    def delete(self, scenario_id: int) -> bool: ...


class HospitalRepository(Protocol):
    def create(self, hospital: Hospital) -> Hospital | None: ...

    def get(self, hospital_id: int) -> Hospital | None: ...

    def get_all(self) -> list[Hospital]: ...

    def update(self, hospital: Hospital) -> Hospital | None: ...

    def delete(self, hospital_id: int) -> bool: ...


class JobRepository(Protocol):
    def create(self, job: SolverJob) -> SolverJob | None: ...

    def get(self, job_id: int) -> SolverJob | None: ...

    def get_all(self) -> list[SolverJob]: ...

    def update(self, job: SolverJob) -> SolverJob | None: ...

    def add_log_entry(self, job_id: int, log_entry: LogEntry) -> bool: ...

    def delete(self, job_id: int) -> bool: ...


class SolutionRepository(Protocol):
    def create(self, solution: Solution) -> Solution | None: ...

    def get(self, solution_id: int) -> Solution | None: ...

    def get_all(self, scenario_id: int | None) -> list[Solution]: ...

    def update(self, solution: Solution) -> Solution | None: ...

    def delete(self, solution_id: int) -> bool: ...


class DistanceRepository(Protocol):
    def get(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst: list[tuple[int, int]],
    ) -> list[tuple[int, int, float, float]] | None: ...

    def update(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst: list[tuple[int, int, float, float]],
    ) -> bool: ...

    def delete(
        self, src_lat_e6: int, src_lng_e6: int, dst_lat_e6: int, dst_lng_e6: int
    ) -> bool: ...


class GeometryRepository(Protocol):
    def get(
        self, src_lat_e6: int, src_lng_e6: int, dst_lat_e6: int, dst_lng_e6: int
    ) -> list[tuple[int, int]] | None: ...

    def update(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst_lat_e6: int,
        dst_lng_e6: int,
        geometry: list[tuple[int, int]],
    ) -> bool: ...

    def delete(
        self, src_lat_e6: int, src_lng_e6: int, dst_lat_e6: int, dst_lng_e6: int
    ) -> bool: ...


class Repositories(Protocol):
    scenarios: ScenarioRepository
    jobs: JobRepository
    geometries: GeometryRepository
    distances: DistanceRepository
    hospitals: HospitalRepository
    solutions: SolutionRepository


class RoutingProvider(Protocol):
    def get_geometry(
        self, src_lat_e6: int, src_lng_e6: int, dst_lat_e6: int, dst_lng_e6: int
    ) -> list[tuple[int, int]]: ...

    def get_distance_and_time(
        self, src_lat_e6: int, src_lng_e6: int, dst: list[tuple[int, int]]
    ) -> list[tuple[float, float]]: ...

    def get_snap_location(self, lat_e6: int, lng_e6: int) -> tuple[int, int, float]: ...
