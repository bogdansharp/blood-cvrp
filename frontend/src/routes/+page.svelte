<svelte:options runes={false} />

<script lang="ts">
    import { onDestroy, onMount } from 'svelte';

    import JobsSection from '$lib/components/JobsSection.svelte';
    import MapView from '$lib/components/MapView.svelte';
    import ScenarioEditor from '$lib/components/ScenarioEditor.svelte';
    import ScenarioSection from '$lib/components/ScenarioSection.svelte';
    import TopBar from '$lib/components/TopBar.svelte';

    import {
        cloneScenario,
        locationKey,
        makeHospitalFromSnappedPoint,
        toE6
    } from '$lib/scenarioEditorHelpers';

    import {
        createInitialState,
        createStore,
        type AppViewState,
        type ClarkeWrightLocalSearch,
        type Hospital,
        type ORFirstSolutionStrategy,
        type ORLocalSearchMetaheuristic,
        type ScenarioPayload,
        type SolveMethod
    } from '$lib/store';

    const defaultSolveMethod: SolveMethod = 'clarke_wright_savings';

    const store = createStore();

    let state: AppViewState = createInitialState();

    let selectedMethod: SolveMethod = defaultSolveMethod;
    let orLocalSearch: ORLocalSearchMetaheuristic = 'NONE';
    let orFirstSolution: ORFirstSolutionStrategy = 'AUTOMATIC';
    let orBalanceRoutes = false;
    let clarkeLocalSearch: ClarkeWrightLocalSearch = 'NONE';
    let timeLimitHours = 9;

    let editorMode = false;
    let scenarioToEdit: ScenarioPayload | null = null;
    let editorDraft: ScenarioPayload | null = null;
    let addDepotMode = false;
    let editorVersion = 0;

    let sidebarOpen = false;

    const unsubscribe = store.subscribe((value) => {
        state = value;
    });

    onMount(() => {
        void store.loadScenarioList();
        void store.fetchHospitals();
    });

    onDestroy(() => {
        unsubscribe();
    });

    const refreshEditorMap = (): void => {
        editorVersion += 1;
    };

    const setEditorDraft = (draft: ScenarioPayload): void => {
        editorDraft = draft;
        refreshEditorMap();
    };

    const handleScenarioChange = (scenarioId: number | null) => {
        if (scenarioId === null) {
            store.resetScenario();
            return;
        }

        selectedMethod = defaultSolveMethod;
        void store.loadScenario(scenarioId);
    };

    const submitAndTrack = async (method: SolveMethod, limitHours: number) => {
        const job = await store.submitSolveRequest(
            method,
            limitHours,
            orFirstSolution,
            orLocalSearch,
            clarkeLocalSearch,
            orBalanceRoutes
        );

        const terminalJob = await store.pollJobUntilTerminal(job.id, 100, 1000);

        if (terminalJob.status === 'finished' && terminalJob.solution_id) {
            await store.loadSolution(terminalJob.solution_id);
        }
    };

    const enterEditorMode = (scenario: ScenarioPayload | null = null): void => {
        scenarioToEdit = scenario;
        editorDraft = cloneScenario(scenario);
        addDepotMode = false;
        editorMode = true;
        sidebarOpen = true;
        store.resetScenario();
        refreshEditorMap();
    };

    const exitEditorMode = async (scenario: ScenarioPayload | null = null): Promise<void> => {
        const editedScenarioId = scenarioToEdit?.id ?? null;

        if (scenario) {
            const scenarioId = await store.saveScenario(scenario);

            if (scenarioId !== null) {
                await store.loadScenarioList();
                await store.loadScenario(scenarioId);
            }
        } else if (editedScenarioId !== null) {
            await store.loadScenario(editedScenarioId);
        } else {
            store.resetScenario();
        }

        editorMode = false;
        scenarioToEdit = null;
        editorDraft = null;
        addDepotMode = false;
        refreshEditorMap();
    };

    const addEditorLocation = (location: Hospital): void => {
        if (!editorDraft) {
            return;
        }

        const key = locationKey(location);

        if (addDepotMode) {
            setEditorDraft({
                ...editorDraft,
                depots: [{ ...location, demand: 0 }],
                customers: editorDraft.customers.filter((customer) => locationKey(customer) !== key)
            });

            addDepotMode = false;
            refreshEditorMap();
            return;
        }

        const alreadySelected =
            editorDraft.customers.some((customer) => locationKey(customer) === key) ||
            editorDraft.depots.some((depot) => locationKey(depot) === key);

        if (alreadySelected) {
            return;
        }

        setEditorDraft({
            ...editorDraft,
            customers: [...editorDraft.customers, { ...location }]
        });
    };

    const removeEditorLocation = (location: Hospital): void => {
        if (!editorDraft) {
            return;
        }

        const key = locationKey(location);

        setEditorDraft({
            ...editorDraft,
            depots: editorDraft.depots.filter((depot) => locationKey(depot) !== key),
            customers: editorDraft.customers.filter((customer) => locationKey(customer) !== key)
        });
    };

    const startDepotSelection = (): void => {
        addDepotMode = true;
        refreshEditorMap();
    };

    const cancelDepotSelection = (): void => {
        addDepotMode = false;
        refreshEditorMap();
    };

    const makeHospitalFromMapPoint = async (lat: number, lng: number): Promise<Hospital | null> => {
        try {
            const [snappedLatE6, snappedLngE6, snapDistanceM] = await store.snapLocation(
                toE6(lat),
                toE6(lng)
            );

            return makeHospitalFromSnappedPoint(
                lat,
                lng,
                snappedLatE6,
                snappedLngE6,
                snapDistanceM
            );
        } catch {
            return null;
        }
    };
</script>

<main class="min-h-dvh w-full bg-white text-neutral-950 min-[821px]:grid min-[821px]:h-dvh min-[821px]:w-screen min-[821px]:grid-rows-[auto_minmax(0,1fr)] min-[821px]:overflow-hidden">
    <TopBar
        {state}
        bind:selectedMethod
        bind:orLocalSearch
        bind:orFirstSolution
        bind:orBalanceRoutes
        bind:clarkeLocalSearch
        bind:timeLimitHours
        {editorMode}
        onScenarioChange={handleScenarioChange}
        onAddScenario={() => enterEditorMode(null)}
        onSolve={() => submitAndTrack(selectedMethod, timeLimitHours)}
    />

    <div class="relative w-full overflow-visible min-[821px]:mb-1.25 min-[821px]:min-h-0 min-[821px]:overflow-hidden">
        <MapView
            {state}
            {editorMode}
            {editorDraft}
            {addDepotMode}
            {editorVersion}
            {addEditorLocation}
            {removeEditorLocation}
            {makeHospitalFromMapPoint}
        />

        <button
            type="button"
            class={`hidden cursor-pointer bg-white text-neutral-950 min-[821px]:absolute min-[821px]:top-1/2 min-[821px]:z-1002 min-[821px]:grid min-[821px]:place-items-center min-[821px]:border min-[821px]:border-r-0 min-[821px]:border-neutral-400 min-[821px]:rounded-l-lg min-[821px]:-translate-y-1/2 ${
                sidebarOpen
                    ? 'min-[821px]:right-[calc(clamp(280px,26vw,380px)+5px)] min-[821px]:h-12 min-[821px]:w-7.5 min-[821px]:p-1'
                    : 'min-[821px]:right-1.25 min-[821px]:min-h-26 min-[821px]:w-9.5 min-[821px]:gap-1 min-[821px]:px-1 min-[821px]:py-2'
            }`}
            onclick={() => (sidebarOpen = !sidebarOpen)}
            aria-expanded={sidebarOpen}
            aria-controls="map-sidebar"
            aria-label={sidebarOpen ? 'Hide details panel' : 'Show details panel'}
        >
            <span class={sidebarOpen ? 'text-2xl leading-none' : 'text-[28px] leading-none'}>
                {sidebarOpen ? '›' : '‹'}
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
            <div class="grid min-w-0 gap-2 overflow-x-auto p-2 min-[821px]:flex min-[821px]:min-h-full min-[821px]:min-w-80 min-[821px]:flex-col">
                {#if editorMode && editorDraft}
                    <section class="min-h-40 overflow-auto border border-neutral-200 bg-white p-2 min-[821px]:min-h-0 min-[821px]:flex-1">
                        <ScenarioEditor
                            draft={editorDraft}
                            addingDepot={addDepotMode}
                            setDraft={setEditorDraft}
                            startDepotSelection={startDepotSelection}
                            cancelDepotSelection={cancelDepotSelection}
                            endEditing={exitEditorMode}
                        />
                    </section>
                {:else}
                    <section class="min-h-40 overflow-auto border border-neutral-200 bg-white p-2 min-[821px]:min-h-0 min-[821px]:flex-1">
                        <ScenarioSection
                            scenario={state.scenario}
                            loading={state.loading}
                            deleteScenario={store.deleteScenario}
                            editScenario={enterEditorMode}
                        />
                    </section>

                    <section class="min-h-40 overflow-auto border border-neutral-200 bg-white p-2 min-[821px]:min-h-0 min-[821px]:flex-1">
                        <JobsSection jobs={state.jobs} />
                    </section>
                {/if}
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