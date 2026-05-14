<svelte:options runes={false} />

<script lang="ts">
    import type { LayerGroup, Map as LeafletMap } from 'leaflet';
    import { onDestroy, onMount } from 'svelte';
    import 'leaflet/dist/leaflet.css';
    import { CLARKE_WRIGHT_LOCAL_SEARCH_LABELS, createInitialState, createStore, OR_FIRST_SOLUTION_STRATEGY_LABELS, OR_LOCAL_SEARCH_METAHEURISTIC_LABELS, SOLVE_METHOD_LABELS, type AppViewState, type ClarkeWrightLocalSearch, type ORFirstSolutionStrategy, type ORLocalSearchMetaheuristic, type ScenarioPayload, type SolveMethod } from '$lib/store';
    import JobsSection from '$lib/components/JobsSection.svelte';
    import ScenarioSection from '$lib/components/ScenarioSection.svelte';
    import ScenarioEditor from '$lib/components/ScenarioEditor.svelte';
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
    let editorMode = false;
    let scenarioToEdit: ScenarioPayload | null = null;

    const enterEditorMode = (scenario: ScenarioPayload | null = null): void => {
        editorMode = true;
        scenarioToEdit = scenario;
        store.resetScenario();
    };

    const exitEditorMode = (scenario: ScenarioPayload | null = null): void => {
        editorMode = false;
        scenarioToEdit = null;
    };

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
                <p class="m-0 text-xs leading-tight text-red-700 min-[821px]:max-w-45 min-[821px]:wrap-break-words">
                    {state.error}
                </p>
            {/if}
        </div>

        <div 
            class="grid min-w-0 grid-cols-1 gap-2 min-[520px]:grid-cols-2 min-[821px]:flex min-[821px]:flex-wrap min-[821px]:items-end min-[821px]:justify-end"
        >
            <div class="grid min-w-0 gap-1 min-[821px]:w-42.5">
                <label class="text-[11px] leading-none text-neutral-600" for="scenario-select">
                    Scenario
                </label>
                <select
                    class="h-7.5 w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950"
                    id="scenario-select"
                    onchange={handleScenarioChange}
                    disabled={state.loading || editorMode}
                >
                    <option value="">Select Scenario</option>
                    {#each state.scenarios as scenario}
                        <option value={scenario.id} selected={state.scenario?.id === scenario.id}>
                            {scenario.name}
                        </option>
                    {/each}
                </select>
            </div>

            <div class="">
                <button 
                    class="h-7.5 cursor-pointer rounded-md border border-[#0f812a] bg-[#0f812a] px-2.5 text-xs text-white disabled:cursor-not-allowed disabled:opacity-55"
                    type="button"
                    onclick={() => enterEditorMode()}
                    disabled={state.loading || editorMode}
                >
                    +
                </button>
            </div>

            <div class="grid min-w-0 gap-1 min-[821px]:w-45">
                <label class="text-[11px] leading-none text-neutral-600" for="method-select">
                    Method
                </label>
                <select
                    class="h-7.5 w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950"
                    id="method-select"
                    bind:value={selectedMethod}
                >
                    {#each Object.entries(SOLVE_METHOD_LABELS) as [key, label]}
                        <option value={key}>{label}</option>
                    {/each}
                </select>
            </div>

            <div class="grid min-w-0 gap-1 min-[821px]:w-23.75">
                <label class="text-[11px] leading-none text-neutral-600" for="time-limit-input">
                    Limit, hours
                </label>
                <input
                    type="number"
                    min="0"
                    id="time-limit-input"
                    class="h-7.5 w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950"
                    bind:value={timeLimitHours}
                />
            </div>

            <label class="flex h-7.5 items-center gap-2 rounded-md border border-neutral-300 px-2 text-xs text-neutral-700 min-[821px]:mb-0">
                <input
                    type="checkbox"
                    class="h-4 w-4"
                    bind:checked={orBalanceRoutes}
                    disabled={selectedMethod !== 'ortools'}
                />
                Balance
            </label>

            <div class="grid min-w-0 gap-1 min-[821px]:w-42.5">
                <label class="text-[11px] leading-none text-neutral-600" for="or-first-solution-select">
                    First solution
                </label>
                <select
                    class="h-7.5 w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950 disabled:bg-neutral-100"
                    id="or-first-solution-select"
                    bind:value={orFirstSolution}
                    disabled={selectedMethod !== 'ortools'}
                >
                    {#each Object.entries(OR_FIRST_SOLUTION_STRATEGY_LABELS) as [key, label]}
                        <option value={key}>{label}</option>
                    {/each}
                </select>
            </div>

            <div class="grid min-w-0 gap-1 min-[821px]:w-40">
                <label class="text-[11px] leading-none text-neutral-600" for="or-local-search-select">
                    Local search
                </label>
                <select
                    class="h-7.5 w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950 disabled:bg-neutral-100"
                    id="or-local-search-select"
                    bind:value={orLocalSearch}
                    disabled={selectedMethod !== 'ortools'}
                >
                    {#each Object.entries(OR_LOCAL_SEARCH_METAHEURISTIC_LABELS) as [key, label]}
                        <option value={key}>{label}</option>
                    {/each}
                </select>
            </div>

            <div class="grid min-w-0 gap-1 min-[821px]:w-40">
                <label class="text-[11px] leading-none text-neutral-600" for="clarke-local-search-select">
                    Local search
                </label>
                <select
                    class="h-7.5 w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950 disabled:bg-neutral-100"
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
                class="h-7.5 w-full rounded-md border border-[#0f4c81] bg-[#0f4c81] px-4 text-xs text-white disabled:cursor-not-allowed disabled:opacity-55 min-[520px]:col-span-2 min-[821px]:col-span-1 min-[821px]:w-auto cursor-pointer"
                type="button"
                onclick={() => submitAndTrack(selectedMethod, timeLimitHours)}
                disabled={state.loading || !state.scenario || editorMode}
            >
                Solve
            </button>
        </div>
    </header>

    <div class="relative w-full overflow-visible min-[821px]:mb-1.25 min-[821px]:min-h-0 min-[821px]:overflow-hidden">
        <div
            bind:this={mapContainer}
            class="relative h-[54dvh] min-h-70 w-full border-b border-neutral-300 min-[821px]:absolute min-[821px]:inset-0 min-[821px]:h-full min-[821px]:border-b-0"
        ></div>

        <button
            type="button"
            class={`hidden bg-white text-neutral-950 min-[821px]:absolute min-[821px]:top-1/2 min-[821px]:z-1002 min-[821px]:grid min-[821px]:place-items-center min-[821px]:border min-[821px]:border-r-0 min-[821px]:border-neutral-400 min-[821px]:rounded-l-lg min-[821px]:cursor-pointer cursor-pointer min-[821px]:-translate-y-1/2 ${
                sidebarOpen
                    ? 'min-[821px]:right-[calc(clamp(280px,26vw,380px)+5px)] min-[821px]:h-12 min-[821px]:w-7.5 min-[821px]:p-1'
                    : 'min-[821px]:right-1.25 min-[821px]:min-h-26 min-[821px]:w-9.5 min-[821px]:gap-1 min-[821px]:px-1 min-[821px]:py-2'
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
            class={`m-2 block border border-neutral-300 bg-white min-[821px]:absolute min-[821px]:bottom-1.25 min-[821px]:right-1.25 min-[821px]:top-1.25 min-[821px]:z-1000 min-[821px]:m-0 min-[821px]:w-[clamp(280px,26vw,380px)] min-[821px]:overflow-auto min-[821px]:transition-transform min-[821px]:duration-150 ${
                sidebarOpen
                    ? 'min-[821px]:translate-x-0'
                    : 'min-[821px]:translate-x-[calc(100%+12px)]'
            }`}
        >
            <div class="grid min-w-0 gap-2 overflow-x-auto p-2 min-[821px]:flex min-[821px]:min-h-full min-[821px]:min-w-[320px] min-[821px]:flex-col">
                {#if !editorMode}
                    <section 
                        class="min-h-40 overflow-auto border border-neutral-200 bg-white p-2 min-[821px]:min-h-0 min-[821px]:flex-1"
                    >
                        <ScenarioSection scenario={state.scenario} loading={state.loading} deleteScenario={store.deleteScenario} editScenario={enterEditorMode}/>
                    </section>
                {:else}
                    <section 
                        class="min-h-40 overflow-auto border border-neutral-200 bg-white p-2 min-[821px]:min-h-0 min-[821px]:flex-1"
                    >
                        <ScenarioEditor scenario={scenarioToEdit} endEditing={exitEditorMode}/>
                    </section>
                {/if}

                <section 
                    class="min-h-40 overflow-auto border border-neutral-200 bg-white p-2 min-[821px]:min-h-0 min-[821px]:flex-1"
                    hidden={editorMode}
                >
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
