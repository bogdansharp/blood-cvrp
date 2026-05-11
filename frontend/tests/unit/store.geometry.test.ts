import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
    createInitialState,
    createStore,
    makeGeometryKey,
    type Hospital,
    type RoutePath,
    type SolutionPayload
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

const flushPromises = async () => {
    for (let i = 0; i < 7; i++) {
        await Promise.resolve();
    }
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

const depot = makeHospital({
    id: 100,
    name: 'Depot',
    lat_e6: 53100000,
    lng_e6: -8200000,
    lat: 53.1,
    lng: -8.2,
    demand: 0
});

const customerA = makeHospital({
    id: 200,
    name: 'Customer A',
    lat_e6: 53200000,
    lng_e6: -8300000,
    lat: 53.2,
    lng: -8.3,
    demand: 4
});

const customerB = makeHospital({
    id: 201,
    name: 'Customer B',
    lat_e6: 53300000,
    lng_e6: -8400000,
    lat: 53.3,
    lng: -8.4,
    demand: 2
});

const makeRoute = (sequence: Hospital[]): RoutePath => {
    const last = sequence.at(-1);
    if (!last) {
        throw new Error('Route sequence must contain at least one hospital');
    }

    return {
        src: sequence[0],
        dst: last,
        sequence,
        total_distance: 1000,
        total_travel_time: 600,
        vehicle_capacity: 10,
        vehicle_capacity_used: 4
    };
};

const makeSolution = (routes: RoutePath[]): SolutionPayload => ({
    id: 7,
    name: 'Solution 7',
    scenario_id: 42,
    method: 'clarke_wright_savings',
    total_distance: 1000,
    total_travel_time: 600,
    routes,
    options: null,
    created_at: '2026-01-01T00:00:00Z'
});

describe('store geometry queue', () => {
    let fetchMock: ReturnType<typeof vi.fn>;

    // Mock global fetch() before each test and restore after
    // Use fake timers to avoid real delays when testing retry logic
    beforeEach(() => {
        vi.useFakeTimers();
        fetchMock = vi.fn();
        vi.stubGlobal('fetch', fetchMock);
    });
    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it('fetches missing geometry after loading a solution', async () => {
        const key = makeGeometryKey(
            depot.lat_e6,
            depot.lng_e6,
            customerA.lat_e6,
            customerA.lng_e6
        );

        const geometry: [number, number][] = [
            [53.1, -8.2],
            [53.15, -8.25],
            [53.2, -8.3]
        ];

        fetchMock
            .mockResolvedValueOnce(jsonResponse(makeSolution([makeRoute([depot, customerA])])))
            .mockResolvedValueOnce(jsonResponse(geometry));

        const store = createStore(apiBase);

        await store.loadSolution(7);
        await flushPromises();

        const state = get(store);

        expect(fetchMock).toHaveBeenCalledTimes(2);
        expect(fetchMock).toHaveBeenNthCalledWith(1, `${apiBase}/solutions/7`);
        expect((fetchMock.mock.calls[1][0] as string)).toContain('/routing/geometry');
        expect(state.geometries.get(key)).toEqual(geometry);
        expect(state.geometryVersion).toBe(1);

        await flushPromises();
    });

    it('does not fetch duplicate route segments more than once', async () => {
        const key = makeGeometryKey(
            depot.lat_e6,
            depot.lng_e6,
            customerA.lat_e6,
            customerA.lng_e6
        );

        const geometry: [number, number][] = [
            [53.1, -8.2],
            [53.2, -8.3]
        ];

        const solution = makeSolution([
            makeRoute([depot, customerA]),
            makeRoute([depot, customerA])
        ]);

        fetchMock
            .mockResolvedValueOnce(jsonResponse(solution))
            .mockResolvedValueOnce(jsonResponse(geometry));

        const store = createStore(apiBase);

        await store.loadSolution(7);
        await flushPromises();

        const state = get(store);

        expect(fetchMock).toHaveBeenCalledTimes(2);
        expect(state.geometries.get(key)).toEqual(geometry);
        expect(state.geometries.size).toBe(1);
        expect(state.geometryVersion).toBe(1);

        await flushPromises();
    });

    it('fetches all missing geometries sequentially', async () => {
        const firstKey = makeGeometryKey(
            depot.lat_e6,
            depot.lng_e6,
            customerA.lat_e6,
            customerA.lng_e6
        );

        const secondKey = makeGeometryKey(
            customerA.lat_e6,
            customerA.lng_e6,
            customerB.lat_e6,
            customerB.lng_e6
        );

        const firstGeometry: [number, number][] = [
            [53.1, -8.2],
            [53.2, -8.3]
        ];

        const secondGeometry: [number, number][] = [
            [53.2, -8.3],
            [53.3, -8.4]
        ];

        fetchMock
            .mockResolvedValueOnce(jsonResponse(makeSolution([makeRoute([depot, customerA, customerB])])))
            .mockResolvedValueOnce(jsonResponse(firstGeometry))
            .mockResolvedValueOnce(jsonResponse(secondGeometry));

        const store = createStore(apiBase);

        await store.loadSolution(7);
        await flushPromises();

        const state = get(store);

        expect(fetchMock).toHaveBeenCalledTimes(3);
        expect(state.geometries.get(firstKey)).toEqual(firstGeometry);
        expect(state.geometries.get(secondKey)).toEqual(secondGeometry);
        expect(state.geometryVersion).toBe(2);
    });

    it('does not fetch geometry that is already cached', async () => {
        const key = makeGeometryKey(
            depot.lat_e6,
            depot.lng_e6,
            customerA.lat_e6,
            customerA.lng_e6
        );

        const cachedGeometry: [number, number][] = [
            [53.1, -8.2],
            [53.2, -8.3]
        ];

        fetchMock.mockResolvedValueOnce(
            jsonResponse(makeSolution([makeRoute([depot, customerA])]))
        );

        const store = createStore(apiBase);

        store.set({
            ...createInitialState(),
            geometries: new Map([[key, cachedGeometry]]),
            geometryVersion: 1
        });

        await store.loadSolution(7);
        await flushPromises();

        const state = get(store);

        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(state.geometries.get(key)).toEqual(cachedGeometry);
        expect(state.geometryVersion).toBe(1);
    });

    it('waits before retrying a failed geometry request', async () => {
        const key = makeGeometryKey(
            depot.lat_e6,
            depot.lng_e6,
            customerA.lat_e6,
            customerA.lng_e6
        );

        const geometry: [number, number][] = [
            [53.1, -8.2],
            [53.2, -8.3]
        ];

        fetchMock
            .mockResolvedValueOnce(jsonResponse(makeSolution([makeRoute([depot, customerA])])))
            .mockResolvedValueOnce(textResponse('Rate limited', 429))
            .mockResolvedValueOnce(jsonResponse(geometry));

        const store = createStore(apiBase);

        await store.loadSolution(7);
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledTimes(2);
        expect(get(store).geometries.has(key)).toBe(false);

        await vi.advanceTimersByTimeAsync(59_999);
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledTimes(2);

        await vi.advanceTimersByTimeAsync(1);
        await flushPromises();

        const state = get(store);

        expect(fetchMock).toHaveBeenCalledTimes(3);
        expect(state.geometries.get(key)).toEqual(geometry);
        expect(state.geometryVersion).toBe(1);

        await flushPromises();
    });

    it('keeps straight-line fallback after geometry fails twice', async () => {
        const key = makeGeometryKey(
            depot.lat_e6,
            depot.lng_e6,
            customerA.lat_e6,
            customerA.lng_e6
        );

        fetchMock
            .mockResolvedValueOnce(jsonResponse(makeSolution([makeRoute([depot, customerA])])))
            .mockResolvedValueOnce(textResponse('Rate limited', 429))
            .mockResolvedValueOnce(textResponse('Still failing', 500));

        const store = createStore(apiBase);

        await store.loadSolution(7);
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledTimes(2);

        await vi.advanceTimersByTimeAsync(60_000);
        await flushPromises();

        const state = get(store);

        expect(fetchMock).toHaveBeenCalledTimes(3);
        expect(state.geometries.has(key)).toBe(false);
        expect(state.geometryVersion).toBe(0);
        expect(state.error).not.toBeNull();
    });
});