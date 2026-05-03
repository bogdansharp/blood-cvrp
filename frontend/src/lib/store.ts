import { writable } from 'svelte/store';

export type SolveMethod =
    | 'clarke_wright_savings'
    | 'clarke_wright_savings_with_2_opt'
    | 'ortools';
export type JobStatus = 'queued' | 'cancelled' | 'running' | 'finished' | 'failed';

export type LogLevel = 'info' | 'warning' | 'error' | 'debug';

export type LogEntry = {
    timestamp: string;
    level: LogLevel;
    message: string;
};

export type VehiclePool = {
    capacity: number;
    quantity: number;
};

export type Hospital = {
    id: number;
    name: string;
    lat_e6: number;
    lng_e6: number;
    display_lat_e6?: number | null;
    display_lng_e6?: number | null;
    snap_distance_m: number;
    category: string;
    subcategory: string;
    address: string;
    eircode: string;
    demand: number;
    lat: number;
    lng: number;
    display_lat: number;
    display_lng: number;
};

export type ScenarioReduced = {
    id: number;
    name: string;
    vehicles_count: number;
    depots_count: number;
    customers_count: number;
    description?: string | null;
};

export type ScenarioPayload = {
    id: number;
    name: string;
    description?: string | null;
    vehicles: VehiclePool[];
    depots: Hospital[];
    customers: Hospital[];
};

export type SolverJobPayload = {
    id: number;
    scenario_id: number;
    method: SolveMethod;
    status: JobStatus;
    name?: string | null;
    log: LogEntry[];
    created_at: string;
    started_at?: string | null;
    finished_at?: string | null;
    solution_id?: number | null;
    solver_ms: number;
    preparation_ms: number;
    results_ms: number;
};

export type RoutePath = {
    src: Hospital;
    dst: Hospital;
    sequence: Hospital[];
    total_distance: number;
    total_travel_time: number;
    vehicle_capacity: number;
    vehicle_capacity_used: number;
};

export type SolutionPayload = {
    id: number;
    name: string;
    scenario_id: number;
    method: SolveMethod;
    total_distance: number;
    total_travel_time: number;
    routes: RoutePath[];
    created_at: string;
};

export type HospitalLocation = {
        id: number;
        name: string;
        lat: number;
        lng: number;
        display_lat: number;
        display_lng: number;
        category: string;
        subcategory: string;
        address: string;
        eircode: string;
        demand: number;
    };

export const isHospitalLocation = (value: unknown): value is HospitalLocation => {
    if (!value || typeof value !== 'object') return false;
    const record = value as Record<string, unknown>;
    return (
        typeof record.id === 'number' &&
        typeof record.name === 'string' &&
        typeof record.lat === 'number' &&
        typeof record.lng === 'number' &&
        typeof record.display_lat === 'number' &&
        typeof record.display_lng === 'number' &&
        typeof record.category === 'string' &&
        typeof record.subcategory === 'string' &&
        typeof record.address === 'string' &&
        typeof record.eircode === 'string' &&
        typeof record.demand === 'number'
    );
};


export type AppViewState = {
    scenario: ScenarioPayload | null;   // Active scenario
    scenarios: ScenarioReduced[];       // List of available scenarios
    jobs: SolverJobPayload[];
    solution: SolutionPayload | null;
    loading: boolean;
    hospitals: HospitalLocation[];
    error: string | null;
};

export const jobStatusLabel = (status: JobStatus): string => {
    return status.charAt(0).toUpperCase() + status.slice(1);
};

const initialState: AppViewState = {
    scenario: null,
    scenarios: [],
    jobs: [],
    solution: null,
    loading: false,
    hospitals: [],
    error: null
};

export const createStore = (apiBase = 'http://localhost:8000/api/v1') => {
    const { subscribe, update, set } = writable<AppViewState>(initialState);

    const upsertJob = (jobs: SolverJobPayload[], job: SolverJobPayload): SolverJobPayload[] => {
        const index = jobs.findIndex((item) => item.id === job.id);
        if (index === -1) return [...jobs, job];
        const next = jobs.slice();
        next[index] = job;
        return next;
    };

    const loadScenarioList = async (): Promise<ScenarioReduced[]> => {
        update((state) => ({ ...state, loading: true, error: null }));

        const listResponse = await fetch(`${apiBase}/scenarios`);
        if (!listResponse.ok) {
            const detail = await listResponse.text();
            // TODO: implement loading IDs set to allow tracking loading state of multiple jobs independently 
            update((state) => ({ ...state, loading: false, error: detail }));
            throw new Error(detail);
        }

        const scenarios = (await listResponse.json()) as ScenarioReduced[];
        if (!scenarios.length) {
            const message = 'No scenarios available.';
            update((state) => ({ ...state, loading: false, error: message }));
            throw new Error(message);
        }

        update((state) => ({ ...state, scenarios, loading: false }));
        return scenarios;
    };

    const loadScenario = async (scenarioId: number): Promise<ScenarioPayload> => {
        update((state) => ({ ...state, loading: true, error: null }));

        const response = await fetch(`${apiBase}/scenarios/${scenarioId}`);
        if (!response.ok) {
            const detail = await response.text();
            update((state) => ({ ...state, loading: false, error: detail }));
            throw new Error(detail);
        }

        const scenario = (await response.json()) as ScenarioPayload;
        update((state) => ({ ...state, scenario, loading: false }));
        return scenario;
    };

    const resetScenario = () => {
        update((state) => ({ ...state, scenario: null, solution: null, error: null }));
    }

    const submitSolveRequest = async (method: SolveMethod): Promise<SolverJobPayload> => {
        let scenarioId: number | null = null;
        update((state) => {
            scenarioId = state.scenario?.id ?? null;
            if (!scenarioId) {
                return { ...state, loading: false, error: 'No scenario loaded.', solution: null };
            }
            return { ...state, loading: true, error: null, solution: null };
        });

        if (!scenarioId) {
            throw new Error('No scenario loaded.');
        }

        const response = await fetch(
            `${apiBase}/jobs/run/${scenarioId}?method=${encodeURIComponent(method)}`,
            { method: 'POST' }
        );

        if (!response.ok) {
            const detail = await response.text();
            update((state) => ({ ...state, loading: false, error: detail }));
            throw new Error(detail);
        }

        const job = (await response.json()) as SolverJobPayload;
        update((state) => ({ ...state, loading: false, jobs: upsertJob(state.jobs, job) }));
        return job;
    };

    const pollJobUntilTerminal = async (
        jobId: number,
        intervalMs = 1000,
        maxPolls = 1000
    ): Promise<SolverJobPayload> => {
        for (let index = 0; index < maxPolls; index += 1) {
            const response = await fetch(`${apiBase}/jobs/${jobId}`);
            if (!response.ok) {
                const detail = await response.text();
                update((state) => ({ ...state, error: detail }));
                throw new Error(detail);
            }

            const job = (await response.json()) as SolverJobPayload;
            update((state) => ({ ...state, jobs: upsertJob(state.jobs, job) }));

            if (job.status === 'finished' || job.status === 'failed' || job.status === 'cancelled') {
                return job;
            }

            await new Promise((resolve) => setTimeout(resolve, intervalMs));
        }

        throw new Error('Job polling timed out');
    };

    const loadSolution = async (solutionId: number): Promise<SolutionPayload> => {
        const response = await fetch(`${apiBase}/solutions/${solutionId}`);
        if (!response.ok) {
            const detail = await response.text();
            update((state) => ({ ...state, error: detail }));
            throw new Error(detail);
        }

        const solution = (await response.json()) as SolutionPayload;
        update((state) => ({ ...state, solution }));
        return solution;
    };

    const fetchHospitals = async () => {
        update((state) => {
            return { ...state, loading: true, error: null, hospitals: [] };
        });

        const listResponse = await fetch(`${apiBase}/hospitals`);
        if (!listResponse.ok) {
            const detail = await listResponse.text();
            update((state) => ({ ...state, loading: false, error: detail }));
            throw new Error(detail);
        }

        const hospitals_raw = (await listResponse.json()) as HospitalLocation[];
        const hospitals = hospitals_raw.filter(isHospitalLocation);
        update((state) => ({ ...state, loading: false, hospitals: hospitals, error: null }));
    };

    return {
        subscribe,
        set,
        reset: () => set(initialState),
        loadScenarioList,
        loadScenario,
        resetScenario,
        submitSolveRequest,
        pollJobUntilTerminal,
        loadSolution,
        fetchHospitals
    };
};
