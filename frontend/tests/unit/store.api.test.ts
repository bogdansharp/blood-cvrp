import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
    createInitialState,
    createStore,
    type Hospital,
    type ScenarioPayload,
    type ScenarioReduced,
    type SolutionPayload,
    type SolverJobPayload
} from '../../src/lib/store';

const apiBase = 'http://test/api/v1';

const jsonResponse = (body: unknown, status = 200): Response => {
    return new Response(JSON.stringify(body), {
        status,
        headers: {
            'Content-Type': 'application/json'
        }
    });
};

const textResponse = (body: string, status = 500): Response => {
    return new Response(body, {
        status,
        headers: {
            'Content-Type': 'text/plain'
        }
    });
};

const makeHospital = (overrides: Partial<Hospital> = {}): Hospital => ({
    id: 1,
    name: 'Hospital 1',
    lat_e6: 53100000,
    lng_e6: -8200000,
    display_lat_e6: 53100000,
    display_lng_e6: -8200000,
    snap_distance_m: 0,
    category: 'Hospital',
    subcategory: 'General',
    address: '1 Main St',
    eircode: 'D91TEST',
    demand: 3,
    lat: 53.1,
    lng: -8.2,
    display_lat: 53.1,
    display_lng: -8.2,
    ...overrides
});

const makeScenario = (overrides: Partial<ScenarioPayload> = {}): ScenarioPayload => ({
    id: 42,
    name: 'Scenario 42',
    description: 'Test scenario',
    vehicles: [{ capacity: 10, quantity: 2 }],
    depots: [makeHospital({ id: 100, name: 'Depot', demand: 0 })],
    customers: [makeHospital({ id: 200, name: 'Customer', demand: 4 })],
    ...overrides
});

const makeScenarioReduced = (
    overrides: Partial<ScenarioReduced> = {}
): ScenarioReduced => ({
    id: 42,
    name: 'Scenario 42',
    vehicles_count: 1,
    depots_count: 1,
    customers_count: 1,
    description: 'Test scenario',
    ...overrides
});

const makeJob = (overrides: Partial<SolverJobPayload> = {}): SolverJobPayload => ({
    id: 10,
    scenario_id: 42,
    method: 'clarke_wright_savings',
    options: null,
    status: 'queued',
    name: 'Test Job',
    log: [],
    created_at: '2026-01-01T00:00:00Z',
    started_at: null,
    finished_at: null,
    solution_id: null,
    solver_ms: 0,
    preparation_ms: 0,
    results_ms: 0,
    ...overrides
});

const makeSolution = (overrides: Partial<SolutionPayload> = {}): SolutionPayload => ({
    id: 7,
    name: 'Solution 7',
    scenario_id: 42,
    method: 'clarke_wright_savings',
    total_distance: 1000,
    total_travel_time: 600,
    routes: [],
    options: null,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides
});

describe('store API/state logic', () => {
    let fetchMock: ReturnType<typeof vi.fn>;

    // Mock global fetch() before each test and restore after
    beforeEach(() => {
        fetchMock = vi.fn();
        vi.stubGlobal('fetch', fetchMock);
    });
    afterEach(() => {
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it('loads and stores scenario list', async () => {
        const scenarios = [
            makeScenarioReduced(),
            makeScenarioReduced({ id: 43, name: 'Scenario 43' })
        ];

        fetchMock.mockResolvedValueOnce(jsonResponse(scenarios));

        const store = createStore(apiBase);
        const result = await store.loadScenarioList();
        const state = get(store);

        expect(result).toEqual(scenarios);
        expect(state.scenarios).toEqual(scenarios);
        expect(state.loading).toBe(false);
        expect(state.error).toBeNull();
        expect(fetchMock).toHaveBeenCalledWith(`${apiBase}/scenarios`);
    });

    it('stores error and clears loading when scenario list request fails', async () => {
        fetchMock.mockResolvedValueOnce(textResponse('Internal server error', 500));

        const store = createStore(apiBase);

        await expect(store.loadScenarioList()).rejects.toThrow('Internal server error');

        const state = get(store);

        expect(state.loading).toBe(false);
        expect(state.error).toBe('Internal server error');
        expect(state.scenarios).toEqual([]);
    });

    it('loads scenario and clears existing solution', async () => {
        const scenario = makeScenario();
        const oldSolution = makeSolution({ id: 99 });

        fetchMock.mockResolvedValueOnce(jsonResponse(scenario));

        const store = createStore(apiBase);
        store.set({
            ...createInitialState(),
            solution: oldSolution
        });

        const result = await store.loadScenario(42);
        const state = get(store);

        expect(result).toEqual(scenario);
        expect(state.scenario).toEqual(scenario);
        expect(state.solution).toBeNull();
        expect(state.loading).toBe(false);
        expect(state.error).toBeNull();
        expect(fetchMock).toHaveBeenCalledWith(`${apiBase}/scenarios/42`);
    });

    it('submits non-OR-Tools solve request with expected params', async () => {
        const job = makeJob();

        fetchMock.mockResolvedValueOnce(jsonResponse(job));

        const store = createStore(apiBase);
        store.set({
            ...createInitialState(),
            scenario: makeScenario()
        });

        const result = await store.submitSolveRequest(
            'clarke_wright_savings', 2, 'AUTOMATIC', 'NONE', false
        );

        const calledUrl = fetchMock.mock.calls[0][0] as string;
        const calledOptions = fetchMock.mock.calls[0][1] as RequestInit;
        const url = new URL(calledUrl);

        expect(result).toEqual(job);
        expect(calledOptions).toEqual({ method: 'POST' });
        expect(url.pathname).toBe('/api/v1/jobs/run/42');
        expect(url.searchParams.get('method')).toBe('clarke_wright_savings');
        expect(url.searchParams.get('cost_limit')).toBe('7200');
        expect(url.searchParams.has('or_first_solution')).toBe(false);
        expect(url.searchParams.has('or_local_search')).toBe(false);
        expect(url.searchParams.has('or_balance_routes')).toBe(false);
        expect(get(store).jobs).toEqual([job]);
    });

    it('submits OR-Tools solve request with OR-specific params', async () => {
        const job = makeJob({ method: 'ortools' });

        fetchMock.mockResolvedValueOnce(jsonResponse(job));

        const store = createStore(apiBase);
        store.set({
            ...createInitialState(),
            scenario: makeScenario()
        });

        await store.submitSolveRequest(
            'ortools', 1.5, 'PATH_CHEAPEST_ARC', 'GUIDED_LOCAL_SEARCH', true
        );

        const calledUrl = fetchMock.mock.calls[0][0] as string;
        const url = new URL(calledUrl);

        expect(url.pathname).toBe('/api/v1/jobs/run/42');
        expect(url.searchParams.get('method')).toBe('ortools');
        expect(url.searchParams.get('cost_limit')).toBe('5400');
        expect(url.searchParams.get('or_first_solution')).toBe('PATH_CHEAPEST_ARC');
        expect(url.searchParams.get('or_local_search')).toBe('GUIDED_LOCAL_SEARCH');
        expect(url.searchParams.get('or_balance_routes')).toBe('true');
    });

    it('does not submit solve request when no scenario is loaded', async () => {
        const store = createStore(apiBase);

        await expect(
            store.submitSolveRequest(
                'clarke_wright_savings', 1, 'AUTOMATIC', 'NONE', false
            )
        ).rejects.toThrow('No scenario loaded.');

        const state = get(store);

        expect(fetchMock).not.toHaveBeenCalled();
        expect(state.error).toBe('No scenario loaded.');
    });

    it('polls job until terminal status and updates jobs', async () => {
        const runningJob = makeJob({ status: 'running' });
        const finishedJob = makeJob({
            status: 'finished',
            solution_id: 7,
            solver_ms: 123
        });

        fetchMock
            .mockResolvedValueOnce(jsonResponse(runningJob))
            .mockResolvedValueOnce(jsonResponse(runningJob))
            .mockResolvedValueOnce(jsonResponse(finishedJob));

        const store = createStore(apiBase);

        const result = await store.pollJobUntilTerminal(10, 1, 5);
        const state = get(store);

        expect(result).toEqual(finishedJob);
        expect(state.jobs).toEqual([finishedJob]);
        expect(fetchMock).toHaveBeenCalledTimes(3);
        expect(fetchMock).toHaveBeenNthCalledWith(1, `${apiBase}/jobs/10`);
        expect(fetchMock).toHaveBeenNthCalledWith(2, `${apiBase}/jobs/10`);
        expect(fetchMock).toHaveBeenNthCalledWith(3, `${apiBase}/jobs/10`);
    });

    it('loads and stores solution', async () => {
        const solution = makeSolution();

        fetchMock.mockResolvedValueOnce(jsonResponse(solution));

        const store = createStore(apiBase);

        const result = await store.loadSolution(7);
        const state = get(store);

        expect(result).toEqual(solution);
        expect(state.solution).toEqual(solution);
        expect(state.error).toBeNull();
        expect(fetchMock).toHaveBeenCalledWith(`${apiBase}/solutions/7`);
    });

    it('resets selected scenario state', () => {
        const store = createStore(apiBase);

        store.set({
            ...createInitialState(),
            scenario: makeScenario(),
            solution: makeSolution(),
            error: 'Old error'
        });

        store.resetScenario();

        const state = get(store);

        expect(state.scenario).toBeNull();
        expect(state.solution).toBeNull();
        expect(state.error).toBeNull();
    });
});