<svelte:options runes={false} />

<script lang="ts">
    import type { LayerGroup, Map as LeafletMap } from 'leaflet';
    import { onDestroy, onMount } from 'svelte';
    import 'leaflet/dist/leaflet.css';
    import { CLARKE_WRIGHT_LOCAL_SEARCH_LABELS, createInitialState, createStore, OR_FIRST_SOLUTION_STRATEGY_LABELS, OR_LOCAL_SEARCH_METAHEURISTIC_LABELS, SOLVE_METHOD_LABELS, type AppViewState, type ClarkeWrightLocalSearch, type ORFirstSolutionStrategy, type ORLocalSearchMetaheuristic, type SolveMethod } from '$lib/store';
    import JobsSection from '$lib/components/JobsSection.svelte';
    import ScenarioSection from '$lib/components/ScenarioSection.svelte';
	import { getBearingDegrees } from '$lib/mapHelpers';

    const defaultCenter: [number, number] = [53.331, -8.092];
    const defaultZoom = 8;

    const defaultSolveMethod: SolveMethod = 'clarke_wright_savings';

    const store = createStore();

    let state: AppViewState = createInitialState();

    let mapContainer: HTMLDivElement | null = null;
    let map: LeafletMap | null = null;
    let mapLayers: LayerGroup | null = null;
    let leaflet: typeof import('leaflet') | null = null;
    let selectedMethod: SolveMethod = defaultSolveMethod;
    let orLocalSearch: ORLocalSearchMetaheuristic = 'NONE';
    let orFirstSolution: ORFirstSolutionStrategy = 'AUTOMATIC';
    let orBalanceRoutes: boolean = false;
    let clarkeLocalSearch: ClarkeWrightLocalSearch = 'NONE';
    let timeLimitHours: number = 9;
    let lastMapKey = '';
    let lastFitBoundsKey = '';

    const unsubscribe = store.subscribe((value) => {
        state = value;
    });

    const ensureMap = async () => {
        if (map || !mapContainer) {
            return;
        }

        const loaded = await import('leaflet');
        leaflet = loaded;
        map = loaded.map(mapContainer).setView(defaultCenter, defaultZoom);
        loaded
            .tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '&copy; OpenStreetMap contributors'
            })
            .addTo(map);
        mapLayers = loaded.layerGroup().addTo(map);
        updateMapLayers();
    };

    const addDirectionArrows = (
        points: [number, number][],
        color: string,
        layers: LayerGroup
    ) => {
        if (!leaflet || points.length < 2) {
            return;
        }

        const arrowCount = Math.min(4, Math.max(1, Math.floor(points.length / 12)));
        const step = Math.max(2, Math.floor(points.length / (arrowCount + 1)));

        for (let index = step; index < points.length; index += step) {
            const previous = points[index - 1];
            const current = points[index];

            const angle = getBearingDegrees(previous, current);

            const icon = leaflet.divIcon({
                className: 'route-arrow-icon',
                html: `
                    <svg
                        width="20" height="20" viewBox="0 0 20 20"
                        style="transform: rotate(${angle}deg);color: ${color};display: block;"
                        aria-hidden="true"
                    >
                        <path d="M10 2 L16 14 L10 11 L4 14 Z" fill="currentColor"/>
                    </svg>
                `,
                iconSize: [20, 20],
                iconAnchor: [10, 10],
            });

            leaflet
                .marker(current, {
                    icon,
                    interactive: false,
                    keyboard: false,
                })
                .addTo(layers);
        }
    };

    const updateMapLayers = (shouldFitBounds = false) => {
        if (!map || !mapLayers || !leaflet) {
            return;
        }

        const layers = mapLayers;
        const l = leaflet;

        layers.clearLayers();

        const scenario = state.scenario;
        const hospitals = state.hospitals;

        if (!scenario && hospitals.length === 0) {
            if (shouldFitBounds) {
                map.setView(defaultCenter, defaultZoom);
            }
            return;
        }

        const bounds: Array<[number, number]> = [];

        if (!scenario) {
            hospitals.forEach((hospital) => {
                const position: [number, number] = [hospital.lat, hospital.lng];
                bounds.push(position);

                l
                    .circleMarker(position, {
                        radius: 5,
                        color: '#555',
                        fillColor: '#555',
                        fillOpacity: 0.7
                    })
                    .bindPopup(`<strong>Hospital:</strong> ${hospital.name}`)
                    .addTo(layers);
            });

            if (bounds.length > 0 && shouldFitBounds) {
                map.fitBounds(bounds, { padding: [24, 24] });
            }

            return;
        }

        scenario.customers.forEach((customer) => {
            const position: [number, number] = [customer.lat, customer.lng];
            bounds.push(position);

            l
                .circleMarker(position, {
                    radius: 5,
                    color: '#b23b00',
                    fillColor: '#b23b00',
                    fillOpacity: 0.7
                })
                .bindPopup(
                    `<strong>Customer:</strong> ${customer.name}<br />Demand: ${customer.demand}`
                )
                .addTo(layers);
        });

        if (state.solution) {
            state.solution.routes.forEach((route, routeIndex) => {
                const routePoints: [number, number][] = [];

                const routeColors = [
                    '#0f4c81', '#b23b00', '#1f7a3f', '#7c3aed',
                    '#c2410c', '#be123c', '#0f766e', '#a16207'
                ];

                let previous: typeof route.sequence[number] | null = null;

                route.sequence.forEach((current) => {
                    if (
                        !Number.isFinite(current.lat) ||
                        !Number.isFinite(current.lng) ||
                        !Number.isFinite(current.lat_e6) ||
                        !Number.isFinite(current.lng_e6)
                    ) {
                        console.warn('Route hospital has invalid coordinates', current);
                        return;
                    }

                    bounds.push([current.lat, current.lng]);

                    if (previous) {
                        const key = `${previous.lat_e6}_${previous.lng_e6}_${current.lat_e6}_${current.lng_e6}`;
                        const geometry = state.geometries.get(key);

                        if (geometry && geometry.length >= 2) {
                            routePoints.push(...geometry);
                        } else {
                            routePoints.push(
                                [previous.lat, previous.lng],
                                [current.lat, current.lng]
                            );
                        }
                    }

                    previous = current;
                });

                if (routePoints.length >= 2) {
                    const distanceKm = (route.total_distance / 1000).toFixed(3);

                    const totalMinutes = Math.round(route.total_travel_time / 60);
                    const hours = Math.floor(totalMinutes / 60);
                    const minutes = totalMinutes % 60;
                    const formattedTime = `${hours}h ${String(minutes).padStart(2, '0')}m`;
                    const routeColor = routeColors[routeIndex % routeColors.length];

                    l
                        .polyline(routePoints, { color: routeColor, weight: 3, opacity: 0.8 })
                        .bindPopup(
                            `Route ${routeIndex + 1}<br />` +
                            `Distance: ${distanceKm} km<br />` +
                            `Time: ${formattedTime} <br />` +
                            `Capacity: ${route.vehicle_capacity_used} / ${route.vehicle_capacity}`
                        )
                        .addTo(layers);

                    addDirectionArrows(routePoints, routeColor, layers);
                }
            });
        }

        scenario.depots.forEach((depot) => {
            const position: [number, number] = [depot.lat, depot.lng];
            bounds.push(position);

            l
                .circleMarker(position, {
                    radius: 7,
                    color: '#0f4c81',
                    fillColor: '#0f4c81',
                    fillOpacity: 0.9
                })
                .bindPopup(`<strong>Depot:</strong> ${depot.name}`)
                .addTo(layers);
        });

        if (shouldFitBounds) {
            if (bounds.length > 0) {
                map.fitBounds(bounds, { padding: [24, 24] });
            } else{
                map.setView(defaultCenter, defaultZoom);
            }
        }
    };

    onMount(() => {
        void store.loadScenarioList();
        void store.fetchHospitals();
        void ensureMap();

        return () => {
            if (map) {
                map.remove();
                map = null;
                mapLayers = null;
                leaflet = null;
            }
        };
    });

    const submitAndTrack = async (method: SolveMethod, timeLimitHours: number) => {
        const job = await store.submitSolveRequest(method, timeLimitHours, orFirstSolution, orLocalSearch, clarkeLocalSearch, orBalanceRoutes);
        const terminalJob = await store.pollJobUntilTerminal(job.id, 100, 1000);
        if (terminalJob.status === 'finished' && terminalJob.solution_id) {
            await store.loadSolution(terminalJob.solution_id);
        }
    };

    const handleScenarioChange = (event: Event) => {
        const rawValue = (event.target as HTMLSelectElement).value;
        if (!rawValue) {
            store.resetScenario();
            return;
        }
        const value = Number(rawValue);
        if (Number.isNaN(value)) {
            store.resetScenario();
            return;
        }
        selectedMethod = defaultSolveMethod;
        void store.loadScenario(value);
    };

    const getMapKey = (value: AppViewState) => {
        const scnId = value.scenario?.id ?? 'none';
        const solId = value.solution?.id ?? 'none';
        const hospCount = value.hospitals.length;
        const routesCount = value.solution?.routes.length ?? 0;
        const geomVer = value.geometryVersion;
        return `${scnId}|${solId}|${hospCount}|${routesCount}|${geomVer}`;
    };

    const getFitBoundsKey = (value: AppViewState) => {
        const scnId = value.scenario?.id ?? 'none';
        const hospCount = value.hospitals.length;
        const depotsCount = value.scenario?.depots.length ?? 0;
        const cstmCount = value.scenario?.customers.length ?? 0;

        return `${scnId}|${hospCount}|${depotsCount}|${cstmCount}`;
    };

    $: if (map && mapLayers && leaflet) {
        const nextMapKey = getMapKey(state);
        const nextFitBoundsKey = getFitBoundsKey(state);

        if (nextMapKey !== lastMapKey) {
            const shouldFitBounds = nextFitBoundsKey !== lastFitBoundsKey;

            lastMapKey = nextMapKey;
            lastFitBoundsKey = nextFitBoundsKey;

            updateMapLayers(shouldFitBounds);
        }
    }

    onDestroy(() => {
        unsubscribe();
    });

    let sidebarOpen = false;
</script>


<main class="min-h-dvh w-full bg-white text-neutral-950 min-[821px]:grid min-[821px]:h-dvh min-[821px]:w-screen min-[821px]:grid-rows-[auto_minmax(0,1fr)] min-[821px]:overflow-hidden">
    <header class="z-20 grid gap-2 border-b border-neutral-300 bg-white p-2 min-[821px]:grid-cols-[180px_minmax(0,1fr)] min-[821px]:items-start min-[821px]:gap-3 min-[821px]:px-3">
        <div class="min-w-0">
            <h1 class="m-0 text-base font-semibold leading-tight min-[821px]:text-lg">
                Blood CVRP App
            </h1>

            {#if state.error}
                <p class="m-0 text-xs leading-tight text-red-700 min-[821px]:max-w-[180px] min-[821px]:break-words">
                    {state.error}
                </p>
            {/if}
        </div>

        <div class="grid min-w-0 grid-cols-1 gap-2 min-[520px]:grid-cols-2 min-[821px]:flex min-[821px]:flex-wrap min-[821px]:items-end min-[821px]:justify-end">
            <div class="grid min-w-0 gap-1 min-[821px]:w-[170px]">
                <label class="text-[11px] leading-none text-neutral-600" for="scenario-select">
                    Scenario
                </label>
                <select
                    class="h-[30px] w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950"
                    id="scenario-select"
                    onchange={handleScenarioChange}
                    disabled={state.loading}
                >
                    <option value="">Select Scenario</option>
                    {#each state.scenarios as scenario}
                        <option value={scenario.id} selected={state.scenario?.id === scenario.id}>
                            {scenario.name}
                        </option>
                    {/each}
                </select>
            </div>

            <div class="grid min-w-0 gap-1 min-[821px]:w-[180px]">
                <label class="text-[11px] leading-none text-neutral-600" for="method-select">
                    Method
                </label>
                <select
                    class="h-[30px] w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950"
                    id="method-select"
                    bind:value={selectedMethod}
                >
                    {#each Object.entries(SOLVE_METHOD_LABELS) as [key, label]}
                        <option value={key}>{label}</option>
                    {/each}
                </select>
            </div>

            <div class="grid min-w-0 gap-1 min-[821px]:w-[95px]">
                <label class="text-[11px] leading-none text-neutral-600" for="time-limit-input">
                    Limit, hours
                </label>
                <input
                    type="number"
                    min="0"
                    id="time-limit-input"
                    class="h-[30px] w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950"
                    bind:value={timeLimitHours}
                />
            </div>

            <label class="flex h-[30px] items-center gap-2 rounded-md border border-neutral-300 px-2 text-xs text-neutral-700 min-[821px]:mb-0">
                <input
                    type="checkbox"
                    class="h-4 w-4"
                    bind:checked={orBalanceRoutes}
                    disabled={selectedMethod !== 'ortools'}
                />
                Balance
            </label>

            <div class="grid min-w-0 gap-1 min-[821px]:w-[170px]">
                <label class="text-[11px] leading-none text-neutral-600" for="or-first-solution-select">
                    First solution
                </label>
                <select
                    class="h-[30px] w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950 disabled:bg-neutral-100"
                    id="or-first-solution-select"
                    bind:value={orFirstSolution}
                    disabled={selectedMethod !== 'ortools'}
                >
                    {#each Object.entries(OR_FIRST_SOLUTION_STRATEGY_LABELS) as [key, label]}
                        <option value={key}>{label}</option>
                    {/each}
                </select>
            </div>

            <div class="grid min-w-0 gap-1 min-[821px]:w-[160px]">
                <label class="text-[11px] leading-none text-neutral-600" for="or-local-search-select">
                    Local search
                </label>
                <select
                    class="h-[30px] w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950 disabled:bg-neutral-100"
                    id="or-local-search-select"
                    bind:value={orLocalSearch}
                    disabled={selectedMethod !== 'ortools'}
                >
                    {#each Object.entries(OR_LOCAL_SEARCH_METAHEURISTIC_LABELS) as [key, label]}
                        <option value={key}>{label}</option>
                    {/each}
                </select>
            </div>

            <div class="grid min-w-0 gap-1 min-[821px]:w-[160px]">
                <label class="text-[11px] leading-none text-neutral-600" for="clarke-local-search-select">
                    Local search
                </label>
                <select
                    class="h-[30px] w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950 disabled:bg-neutral-100"
                    id="clarke-local-search-select"
                    bind:value={clarkeLocalSearch}
                    disabled={selectedMethod !== 'clarke_wright_savings'}
                >
                    {#each Object.entries(CLARKE_WRIGHT_LOCAL_SEARCH_LABELS) as [key, label]}
                        <option value={key}>{label}</option>
                    {/each}
                </select>
            </div>

            <button
                class="h-[30px] w-full rounded-md border border-[#0f4c81] bg-[#0f4c81] px-4 text-xs text-white disabled:cursor-not-allowed disabled:opacity-55 min-[520px]:col-span-2 min-[821px]:col-span-1 min-[821px]:w-auto"
                type="button"
                onclick={() => submitAndTrack(selectedMethod, timeLimitHours)}
                disabled={state.loading || !state.scenario}
            >
                Solve
            </button>
        </div>
    </header>

    <div class="relative w-full overflow-visible min-[821px]:mb-[5px] min-[821px]:min-h-0 min-[821px]:overflow-hidden">
        <div
            bind:this={mapContainer}
            class="relative h-[54dvh] min-h-[280px] w-full border-b border-neutral-300 min-[821px]:absolute min-[821px]:inset-0 min-[821px]:h-full min-[821px]:border-b-0"
        ></div>

        <button
            type="button"
            class={`hidden bg-white text-neutral-950 min-[821px]:absolute min-[821px]:top-1/2 min-[821px]:z-[1002] min-[821px]:grid min-[821px]:place-items-center min-[821px]:border min-[821px]:border-r-0 min-[821px]:border-neutral-400 min-[821px]:rounded-l-lg min-[821px]:cursor-pointer min-[821px]:-translate-y-1/2 ${
                sidebarOpen
                    ? 'min-[821px]:right-[calc(clamp(280px,26vw,380px)+5px)] min-[821px]:h-12 min-[821px]:w-[30px] min-[821px]:p-1'
                    : 'min-[821px]:right-[5px] min-[821px]:min-h-[104px] min-[821px]:w-[38px] min-[821px]:gap-1 min-[821px]:px-1 min-[821px]:py-2'
            }`}
            onclick={() => sidebarOpen = !sidebarOpen}
            aria-expanded={sidebarOpen}
            aria-controls="map-sidebar"
            aria-label={sidebarOpen ? "Hide details panel" : "Show details panel"}
        >
            <span class={sidebarOpen ? "text-2xl leading-none" : "text-[28px] leading-none"}>
                {sidebarOpen ? "›" : "‹"}
            </span>

            {#if !sidebarOpen}
                <span class="[writing-mode:vertical-rl] rotate-180 text-xs uppercase tracking-wide">
                    Details
                </span>
            {/if}
        </button>

        <aside
            id="map-sidebar"
            class={`m-2 block border border-neutral-300 bg-white min-[821px]:absolute min-[821px]:bottom-[5px] min-[821px]:right-[5px] min-[821px]:top-[5px] min-[821px]:z-[1000] min-[821px]:m-0 min-[821px]:w-[clamp(280px,26vw,380px)] min-[821px]:overflow-auto min-[821px]:transition-transform min-[821px]:duration-150 ${
                sidebarOpen
                    ? 'min-[821px]:translate-x-0'
                    : 'min-[821px]:translate-x-[calc(100%+12px)]'
            }`}
        >
            <div class="grid min-w-0 gap-2 overflow-x-auto p-2 min-[821px]:flex min-[821px]:min-h-full min-[821px]:min-w-[320px] min-[821px]:flex-col">
                <section class="min-h-[160px] overflow-auto border border-neutral-200 bg-white p-2 min-[821px]:min-h-0 min-[821px]:flex-1">
                    <ScenarioSection scenario={state.scenario} loading={state.loading} />
                </section>

                <section class="min-h-[160px] overflow-auto border border-neutral-200 bg-white p-2 min-[821px]:min-h-0 min-[821px]:flex-1">
                    <JobsSection jobs={state.jobs} />
                </section>
            </div>
        </aside>
    </div>
</main>


<style>
    :global(html),
    :global(body) {
        margin: 0;
        width: 100%;
        min-height: 100%;
    }

    :global(*) {
        box-sizing: border-box;
    }

    @media (min-width: 821px) {
        :global(html),
        :global(body) {
            height: 100%;
            overflow: hidden;
        }
    }
</style>



<!-- <main>
    <header class="topbar">
        <div class="brand-row">
            <h1>Blood CVRP App</h1>

            {#if state.error}
                <p class="error">{state.error}</p>
            {/if}
        </div>

        <div class="actions">
            <div class="field">
                <label for="scenario-select">Scenario</label>
                <select id="scenario-select" onchange={handleScenarioChange} disabled={state.loading}>
                    <option value="">Select Scenario</option>
                    {#each state.scenarios as scenario}
                        <option value={scenario.id} selected={state.scenario?.id === scenario.id}>
                            {scenario.name}
                        </option>
                    {/each}
                </select>
            </div>

            <div class="field">
                <label for="method-select">Method</label>
                <select id="method-select" bind:value={selectedMethod}>
                    {#each solveMethods as method}
                        <option value={method}>{method}</option>
                    {/each}
                </select>
            </div>

            <button
                class="submit-button"
                type="button"
                onclick={() => submitAndTrack(selectedMethod)}
                disabled={state.loading || !state.scenario}
            >
                Solve
            </button>
        </div>
    </header>

    <div class="map-frame">
        <div bind:this={mapContainer} class="map-container"></div>

        <button
            type="button"
            class="drawer-handle"
            class:open={sidebarOpen}
            onclick={() => sidebarOpen = !sidebarOpen}
            aria-expanded={sidebarOpen}
            aria-controls="map-sidebar"
            aria-label={sidebarOpen ? "Hide details panel" : "Show details panel"}
        >
            <span class="handle-icon">{sidebarOpen ? "›" : "‹"}</span>
            {#if !sidebarOpen}
                <span class="handle-text">Details</span>
            {/if}
        </button>

        <aside
            id="map-sidebar"
            class="map-sidebar"
            class:open={sidebarOpen}
        >
            <div class="sidebar-content">
                <section class="panel scenario-panel">
                    <ScenarioSection scenario={state.scenario} loading={state.loading} />
                </section>

                <section class="panel jobs-panel">
                    <JobsSection jobs={state.jobs} />
                </section>
            </div>
        </aside>
    </div>
</main>


<style>
    :global(html),
    :global(body) {
        margin: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
    }

    :global(*) {
        box-sizing: border-box;
    }

    main {
        --topbar-height: 72px;
        --sidebar-width: clamp(280px, 26vw, 380px);

        width: 100vw;
        height: 100dvh;
        display: grid;
        grid-template-rows: var(--topbar-height) minmax(0, 1fr);
        overflow: hidden;
        color: #111;
        background: #fff;
    }

    .topbar {
        min-width: 0;
        height: var(--topbar-height);
        display: grid;
        grid-template-columns: minmax(190px, auto) minmax(0, 1fr);
        align-items: center;
        gap: 12px;
        padding: 8px 12px;
        border-bottom: 1px solid #d0d0d0;
        background: #fff;
        z-index: 20;
    }

    .brand-row {
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 3px;
    }

    h1 {
        margin: 0;
        font-size: 18px;
        line-height: 1.1;
        font-weight: 650;
        white-space: nowrap;
    }

    .error {
        margin: 0;
        max-width: 280px;
        overflow: hidden;
        color: #b00020;
        font-size: 12px;
        line-height: 1.2;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .actions {
        min-width: 0;
        display: grid;
        grid-template-columns: minmax(140px, 180px) minmax(120px, 160px) auto;
        justify-content: end;
        align-items: end;
        gap: 8px;
    }

    .field {
        min-width: 0;
        display: grid;
        gap: 3px;
    }

    .field label {
        font-size: 11px;
        line-height: 1;
        color: #444;
    }

    .actions select {
        width: 100%;
        min-width: 0;
        height: 30px;
        padding: 3px 8px;
        border: 1px solid #aaa;
        border-radius: 6px;
        background: #fff;
        color: #111;
        font-size: 13px;
    }

    .submit-button {
        height: 30px;
        min-width: 72px;
        padding: 3px 12px;
        border: 1px solid #0f4c81;
        border-radius: 6px;
        background: #0f4c81;
        color: #fff;
        font-size: 13px;
        cursor: pointer;
    }

    .submit-button:disabled {
        opacity: 0.55;
        cursor: not-allowed;
    }

    .map-frame {
        position: relative;
        min-height: 0;
        width: 100%;
        margin-bottom: 5px;
        overflow: hidden;
    }

    .map-container {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
    }

    .map-sidebar {
        position: absolute;
        top: 5px;
        right: 5px;
        bottom: 5px;
        width: var(--sidebar-width);
        z-index: 1000;
        overflow: auto;
        border: 1px solid #c8c8c8;
        background: #fff;
        transform: translateX(calc(100% + 12px));
        transition: transform 160ms ease;
    }

    .map-sidebar.open {
        transform: translateX(0);
    }

    .sidebar-content {
        min-width: 320px;
        min-height: 100%;
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 8px;
        overflow-x: auto;
    }

    .panel {
        flex: 1 1 0;
        min-height: 0;
        overflow: auto;
        padding: 8px;
        border: 1px solid #ddd;
        background: #fff;
    }

    .panel > :global(.scenario),
    .panel > :global(.jobs) {
        margin: 0;
    }

    .drawer-handle {
        position: absolute;
        top: 50%;
        right: 5px;
        z-index: 1002;
        width: 38px;
        min-height: 104px;
        display: grid;
        place-items: center;
        gap: 5px;
        padding: 8px 4px;
        border: 1px solid #aaa;
        border-right: 0;
        border-radius: 10px 0 0 10px;
        background: #fff;
        color: #111;
        cursor: pointer;
        transform: translateY(-50%);
    }

    .drawer-handle.open {
        right: calc(var(--sidebar-width) + 5px);
        width: 30px;
        min-height: 48px;
        padding: 4px 2px;
    }

    .handle-icon {
        font-size: 28px;
        line-height: 1;
    }

    .drawer-handle.open .handle-icon {
        font-size: 24px;
    }

    .handle-text {
        writing-mode: vertical-rl;
        transform: rotate(180deg);
        font-size: 12px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    @media (max-width: 820px) {
        :global(html),
        :global(body) {
            height: auto;
            min-height: 100%;
            overflow-x: hidden;
            overflow-y: auto;
        }

        main {
            width: 100%;
            min-height: 100dvh;
            height: auto;
            display: block;
            overflow: visible;
        }

        .topbar {
            height: auto;
            min-height: 0;
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
            padding: 8px;
        }

        .brand-row {
            min-width: 0;
            display: grid;
            grid-template-columns: 1fr;
            gap: 3px;
        }

        h1 {
            font-size: 16px;
            white-space: normal;
        }

        .error {
            max-width: none;
            white-space: normal;
        }

        .actions {
            width: 100%;
            min-width: 0;
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
            justify-content: stretch;
            align-items: end;
            gap: 6px;
        }

        .actions select {
            width: 100%;
            min-width: 0;
            height: 30px;
            font-size: 12px;
        }

        .submit-button {
            width: auto;
            min-width: 64px;
            height: 30px;
            padding: 3px 10px;
            font-size: 12px;
        }

        .map-frame {
            position: static;
            width: 100%;
            min-height: 0;
            margin: 0;
            overflow: visible;
        }

        .map-container {
            position: relative;
            width: 100%;
            height: 58dvh;
            min-height: 300px;
            border-bottom: 1px solid #ccc;
        }

        .handle-icon {
            font-size: 18px;
            transform: rotate(90deg);
        }

        .drawer-handle.open .handle-icon {
            font-size: 18px;
        }

        .handle-text {
            writing-mode: horizontal-tb;
            transform: none;
            font-size: 12px;
            letter-spacing: 0.02em;
        }

        .drawer-handle {
            display: none;
        }

        .map-sidebar {
            position: static;
            display: block;
            width: auto;
            max-width: none;
            margin: 8px;
            border: 1px solid #c8c8c8;
            transform: none;
            overflow: visible;
        }

        .map-sidebar.open {
            transform: none;
        }

        .sidebar-content {
            min-width: 0;
            width: 100%;
            min-height: 0;
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
            padding: 8px;
            overflow-x: auto;
        }

        .panel {
            min-height: 160px;
            max-height: none;
            overflow: auto;
        }
    }

    @media (max-width: 520px) {
        .actions {
            grid-template-columns: 1fr;
        }

        .submit-button {
            width: 100%;
        }

        .map-container {
            height: 54dvh;
            min-height: 280px;
        }
    }

    @media (max-width: 360px) {
        .topbar {
            padding: 6px;
        }

        .actions {
            gap: 5px;
        }

        .actions select,
        .submit-button {
            height: 28px;
        }

        .map-container {
            height: 50dvh;
            min-height: 250px;
        }
    }
</style> -->