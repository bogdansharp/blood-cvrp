import { get, writable } from 'svelte/store';

export type SolveMethod =
    | 'clarke_wright_savings'
    | 'ortools';

export const SOLVE_METHOD_LABELS: Record<SolveMethod, string> = {
    'clarke_wright_savings': 'Clarke-Wright Savings',
    'ortools': 'OR-Tools',
};

export type SolverObjective = 'minimize_distance' | 'minimize_travel_time';

export type ORFirstSolutionStrategy =
    | 'AUTOMATIC'
    | 'PATH_CHEAPEST_ARC'
    | 'SAVINGS'
    | 'PARALLEL_CHEAPEST_INSERTION'
    | 'LOCAL_CHEAPEST_INSERTION'
    | 'GLOBAL_CHEAPEST_ARC';

export const OR_FIRST_SOLUTION_STRATEGY_LABELS: Record<ORFirstSolutionStrategy, string> = {
    AUTOMATIC: 'Automatic',
    PATH_CHEAPEST_ARC: 'Path cheapest arc',
    SAVINGS: 'Savings',
    PARALLEL_CHEAPEST_INSERTION: 'Parallel cheapest insertion',
    LOCAL_CHEAPEST_INSERTION: 'Local cheapest insertion',
    GLOBAL_CHEAPEST_ARC: 'Global cheapest arc',
};

export type ORLocalSearchMetaheuristic =
    | 'NONE'
    | 'AUTOMATIC'
    | 'GREEDY_DESCENT'
    | 'GUIDED_LOCAL_SEARCH'
    | 'SIMULATED_ANNEALING'
    | 'TABU_SEARCH';

export const OR_LOCAL_SEARCH_METAHEURISTIC_LABELS: Record<ORLocalSearchMetaheuristic, string> = {
    NONE: 'None',
    AUTOMATIC: 'Automatic',
    GREEDY_DESCENT: 'Greedy descent',
    GUIDED_LOCAL_SEARCH: 'Guided local search',
    SIMULATED_ANNEALING: 'Simulated annealing',
    TABU_SEARCH: 'Tabu search',
};

export type ClarkeWrightLocalSearch = 'NONE' | 'TWO_OPT';

export const CLARKE_WRIGHT_LOCAL_SEARCH_LABELS: Record<ClarkeWrightLocalSearch, string> = {
    NONE: 'None',
    TWO_OPT: '2-opt',
};

export type SolveMethodOptions = {
    random_seed?: number | null;
    time_limit_sec?: number | null;
    objective?: SolverObjective;
    cost_limit?: number | null;
    or_balance_routes?: boolean;
    or_target_time_sec?: number;
    or_first_solution_strategy?: ORFirstSolutionStrategy | null;
    or_local_search_metaheuristic?: ORLocalSearchMetaheuristic | null;
    clarke_wright_local_search?: ClarkeWrightLocalSearch | null;
};


export type JobStatus = 'queued' | 'cancelled' | 'running' | 'finished' | 'failed';

export type LogLevel = 'info' | 'warning' | 'error' | 'debug';

export type LogEntry = {
    timestamp: string;
    level: LogLevel;
    message: string;
};

export type VehiclePool = {
    capacity: number;
    quantity: number; // -1 if unlimited
    // time_limit: number; // in seconds, -1 if unlimited
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
    options: SolveMethodOptions | null;
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
    options: SolveMethodOptions | null;
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
    geometries: Map<string, [number, number][]>;
    geometryVersion: number;
};

export const jobStatusLabel = (status: JobStatus): string => {
    return status.charAt(0).toUpperCase() + status.slice(1);
};

export const cancelJob = async (
    jobId: number, 
    apiBase: string = 'http://localhost:8000/api/v1'
): Promise<void> => {
    const response = await fetch(`${apiBase}/jobs/cancel/${jobId}`, { method: 'POST' });
    if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail);
    }
};

export const createInitialState = (): AppViewState => ({
    scenario: null,
    scenarios: [],
    jobs: [],
    solution: null,
    loading: false,
    hospitals: [],
    error: null,
    geometries: new Map(),
    geometryVersion: 0,
});

type GeometryRequest = {
    key: string;
    src_lat_e6: number;
    src_lng_e6: number;
    dst_lat_e6: number;
    dst_lng_e6: number;
    attempts: number;
};

export const makeGeometryKey = (
    src_lat_e6: number,
    src_lng_e6: number,
    dst_lat_e6: number,
    dst_lng_e6: number,
): string => {
    return `${src_lat_e6}_${src_lng_e6}_${dst_lat_e6}_${dst_lng_e6}`;
};

const sleep = (ms: number): Promise<void> => {
    return new Promise((resolve) => setTimeout(resolve, ms));
};

export const createStore = (apiBase = 'http://localhost:8000/api/v1') => {
    const { subscribe, update, set } = writable<AppViewState>(createInitialState());

    let geometryQueue: GeometryRequest[] = [];
    let geometryQueuedKeys = new Set<string>();
    let geometryInProgress = false;
    let currentGeometryKey: string | null = null;
    let geometryCooldownUntil: number | null = null;

    const clearGeometryQueue = () => {
        geometryQueue = [];
        geometryQueuedKeys = new Set<string>();
        currentGeometryKey = null;
        geometryCooldownUntil = null;
    };

    const enqueueGeometriesForSolution = (solution: SolutionPayload) => {
        const snapshot = get({ subscribe });

        for (const route of solution.routes) {
            let previous: Hospital | null = null;

            for (const current of route.sequence) {
                if (previous) {
                    const key = makeGeometryKey(
                        previous.lat_e6,
                        previous.lng_e6,
                        current.lat_e6,
                        current.lng_e6,
                    );

                    const alreadyLoaded = snapshot.geometries.has(key);
                    const alreadyQueued = geometryQueuedKeys.has(key);
                    const currentlyLoading = currentGeometryKey === key;

                    if (!alreadyLoaded && !alreadyQueued && !currentlyLoading) {
                        geometryQueue.push({
                            key,
                            src_lat_e6: previous.lat_e6,
                            src_lng_e6: previous.lng_e6,
                            dst_lat_e6: current.lat_e6,
                            dst_lng_e6: current.lng_e6,
                            attempts: 0,
                        });

                        geometryQueuedKeys.add(key);
                    }
                }

                previous = current;
            }
        }

        void processGeometryQueue();
    };

    const processGeometryQueue = async () => {
        if (geometryInProgress) {
            return;
        }

        geometryInProgress = true;

        try {
            while (geometryQueue.length > 0) {
                if (geometryCooldownUntil && Date.now() < geometryCooldownUntil) {
                    await sleep(geometryCooldownUntil - Date.now());
                }

                const request = geometryQueue.shift();

                if (!request) {
                    continue;
                }

                geometryQueuedKeys.delete(request.key);

                const snapshot = get({ subscribe });

                if (snapshot.geometries.has(request.key)) {
                    continue;
                }

                currentGeometryKey = request.key;

                const response = await fetch(
                    `${apiBase}/routing/geometry?src_lat_e6=${request.src_lat_e6}&src_lng_e6=${request.src_lng_e6}&dst_lat_e6=${request.dst_lat_e6}&dst_lng_e6=${request.dst_lng_e6}`,
                );

                if (!response.ok) {
                    const detail = await response.text();

                    if (request.attempts < 1) {
                        request.attempts += 1;
                        geometryQueue.unshift(request);
                        geometryQueuedKeys.add(request.key);

                        geometryCooldownUntil = Date.now() + 60_000;
                        currentGeometryKey = null;

                        update((state) => ({
                            ...state,
                            error: detail || 'Route geometry request failed. Retrying in 60 seconds.',
                        }));

                        await sleep(60_000);
                        continue;
                    }

                    currentGeometryKey = null;

                    update((state) => ({
                        ...state,
                        error: detail || 'Route geometry request failed. Using straight-line fallback.',
                    }));

                    continue;
                }

                const geometry = (await response.json()) as [number, number][];

                update((state) => {
                    if (state.geometries.has(request.key)) {
                        return state;
                    }

                    const geometries = new Map(state.geometries);
                    geometries.set(request.key, geometry);

                    return {
                        ...state,
                        geometries,
                        geometryVersion: state.geometryVersion + 1,
                        error: null,
                    };
                });

                currentGeometryKey = null;
            }
        } finally {
            geometryInProgress = false;
            currentGeometryKey = null;
        }
    };

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
        clearGeometryQueue();

        update((state) => ({ ...state, loading: true, error: null, solution: null }));

        const response = await fetch(`${apiBase}/scenarios/${scenarioId}`);
        if (!response.ok) {
            const detail = await response.text();
            update((state) => ({ ...state, loading: false, error: detail }));
            throw new Error(detail);
        }

        const scenario = (await response.json()) as ScenarioPayload;
        update((state) => ({ ...state, scenario, loading: false, solution: null }));
        return scenario;
    };

    const loadGeometry = async (
        src_lat_e6: number,
        src_lng_e6: number,
        dst_lat_e6: number,
        dst_lng_e6: number,
    ): Promise<[number, number][]> => {
        const key = makeGeometryKey(src_lat_e6, src_lng_e6, dst_lat_e6, dst_lng_e6);
        const existing = get({ subscribe }).geometries.get(key);

        if (existing) {
            return existing;
        }

        const response = await fetch(
            `${apiBase}/routing/geometry?src_lat_e6=${src_lat_e6}&src_lng_e6=${src_lng_e6}&dst_lat_e6=${dst_lat_e6}&dst_lng_e6=${dst_lng_e6}`,
        );

        if (!response.ok) {
            const detail = await response.text();
            throw new Error(detail);
        }

        const geometry = (await response.json()) as [number, number][];

        update((state) => {
            const geometries = new Map(state.geometries);
            geometries.set(key, geometry);

            return {
                ...state,
                geometries,
                geometryVersion: state.geometryVersion + 1,
            };
        });

        return geometry;
    };

    const resetScenario = () => {
        clearGeometryQueue();
        update((state) => ({ ...state, scenario: null, solution: null, error: null }));
    }

    const submitSolveRequest = async (
        method: SolveMethod, 
        timeLimitHours: number,
        orFirstSolution: ORFirstSolutionStrategy,
        orLocalSearch: ORLocalSearchMetaheuristic,
        clarkeLocalSearch: ClarkeWrightLocalSearch,
        orBalanceRoutes: boolean = false,
    ): Promise<SolverJobPayload> => {
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

        let timeLimitSeconds = Math.round(timeLimitHours * 3600);
        if (timeLimitSeconds < 0) {
            throw new Error('Time limit must be non-negative.');
        }

        let params: string = "";
        if (method === 'ortools') {
            params += `&or_first_solution=${encodeURIComponent(orFirstSolution)}`;
            params += `&or_local_search=${encodeURIComponent(orLocalSearch)}`;
            params += `&or_balance_routes=${orBalanceRoutes}`;
        } else if (method === 'clarke_wright_savings') {
            params += `&clarke_local_search=${encodeURIComponent(clarkeLocalSearch)}`;
        }
        const response = await fetch(
            `${apiBase}/jobs/run/${scenarioId}?method=${encodeURIComponent(method)}&cost_limit=${timeLimitSeconds}${params}`,
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
            update((state) => {
                const existing = state.jobs.find((item) => item.id === job.id);
                if (existing && JSON.stringify(existing) === JSON.stringify(job)) {
                    return state;
                }
                return { ...state, jobs: upsertJob(state.jobs, job) };
            });

            if (job.status === 'finished' || job.status === 'failed' || job.status === 'cancelled') {
                return job;
            }

            await new Promise((resolve) => setTimeout(resolve, intervalMs));
        }

        throw new Error('Job polling timed out');
    };

    const loadSolution = async (solutionId: number): Promise<SolutionPayload> => {
        clearGeometryQueue();

        const response = await fetch(`${apiBase}/solutions/${solutionId}`);
        if (!response.ok) {
            const detail = await response.text();
            update((state) => ({ ...state, error: detail }));
            throw new Error(detail);
        }

        const solution = (await response.json()) as SolutionPayload;
        update((state) => ({ ...state, solution }));
        enqueueGeometriesForSolution(solution);

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

    const deleteScenario = async (scenarioId: number): Promise<void> => {
        const response = await fetch(`${apiBase}/scenarios/${scenarioId}`, { method: 'DELETE' });
        if (response.ok) {
            update((state) => ({
                ...state, 
                scenario: null, 
                solution: null, 
                error: null, 
                scenarios: state.scenarios.filter(s => s.id !== scenarioId) 
            }));
        } else {
            const detail = await response.text();
            console.error(`Failed to delete scenario ${scenarioId}:`, detail);
        }
    };

    return {
        subscribe,
        set,
        reset: () => { clearGeometryQueue(); set(createInitialState()); },
        loadScenarioList,
        loadScenario,
        resetScenario,
        submitSolveRequest,
        pollJobUntilTerminal,
        loadSolution,
        fetchHospitals,
        loadGeometry,
        deleteScenario,
    };
};
