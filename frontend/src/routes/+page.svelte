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
	import SolutionsSection from '$lib/components/SolutionsSection.svelte';

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

	type SidebarTab = 'scenario' | 'solutions' | 'jobs';
	let activeSidebarTab: SidebarTab = 'scenario';

	const unsubscribe = store.subscribe((value) => {
		state = value;
	});

	onMount(() => {
		void store.loadScenarioList();
		void store.fetchHospitals();
		void store.loadSolutionList();
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

		activeSidebarTab = 'scenario';
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
		store.resetScenario();
		refreshEditorMap();
	};

	const exitEditorMode = async (scenario: ScenarioPayload | null = null): Promise<void> => {
		const editedScenarioId = scenarioToEdit?.id ?? null;

		if (scenario) {
			const scenarioId = await store.saveScenario(scenario);

			if (scenarioId !== null) {
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

			return makeHospitalFromSnappedPoint(lat, lng, snappedLatE6, snappedLngE6, snapDistanceM);
		} catch {
			return null;
		}
	};
</script>

<main
	class="min-h-dvh w-full bg-white text-neutral-950 min-[821px]:grid min-[821px]:h-dvh min-[821px]:w-screen min-[821px]:grid-rows-[auto_minmax(0,1fr)] min-[821px]:overflow-hidden"
>
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
		onGeometriesEnabledChange={(enabled) => store.setGeometriesEnabled(enabled)}
	/>

	<div
		class="relative w-full overflow-visible min-[821px]:mb-1.25 min-[821px]:min-h-0 min-[821px]:overflow-hidden"
	>
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

		<aside
			id="map-sidebar"
			class="m-2 block border border-neutral-300 bg-white min-[821px]:absolute min-[821px]:top-1.25 min-[821px]:right-1.25 min-[821px]:bottom-5 min-[821px]:z-1000 min-[821px]:m-0 min-[821px]:w-[clamp(280px,26vw,380px)] min-[821px]:overflow-auto"
		>
			<div
				class="grid min-w-0 gap-2 overflow-x-hidden p-2 min-[821px]:flex min-[821px]:h-full min-[821px]:min-h-0 min-[821px]:flex-col min-[821px]:overflow-hidden"
			>
				{#if editorMode && editorDraft}
					<section
						class="min-h-40 overflow-x-hidden overflow-y-auto border border-neutral-200 bg-white p-2 min-[821px]:min-h-0 min-[821px]:flex-1"
					>
						<ScenarioEditor
							draft={editorDraft}
							addingDepot={addDepotMode}
							setDraft={setEditorDraft}
							{startDepotSelection}
							{cancelDepotSelection}
							endEditing={exitEditorMode}
						/>
					</section>
				{:else}
					<div
						class="grid min-h-0 gap-2 min-[821px]:flex min-[821px]:min-h-0 min-[821px]:flex-1 min-[821px]:flex-col"
					>
						<div class="flex gap-1 border-b border-neutral-200">
							<button
								class={`h-7.5 cursor-pointer rounded-t-md px-3 text-xs ${
									activeSidebarTab === 'scenario'
										? 'bg-[#0f4c81] text-white'
										: 'bg-slate-100 text-slate-700'
								}`}
								type="button"
								onclick={() => (activeSidebarTab = 'scenario')}
							>
								Scenario
							</button>

							<button
								class={`h-7.5 cursor-pointer rounded-t-md px-3 text-xs ${
									activeSidebarTab === 'solutions'
										? 'bg-[#0f4c81] text-white'
										: 'bg-slate-100 text-slate-700'
								}`}
								type="button"
								onclick={() => (activeSidebarTab = 'solutions')}
							>
								Solutions
							</button>

							<button
								class={`h-7.5 cursor-pointer rounded-t-md px-3 text-xs ${
									activeSidebarTab === 'jobs'
										? 'bg-[#0f4c81] text-white'
										: 'bg-slate-100 text-slate-700'
								}`}
								type="button"
								onclick={() => (activeSidebarTab = 'jobs')}
							>
								Jobs
							</button>
						</div>

						<section
							class="min-h-40 overflow-x-hidden overflow-y-auto border border-neutral-200 bg-white p-2 min-[821px]:min-h-0 min-[821px]:flex-1"
						>
							{#if activeSidebarTab === 'scenario'}
								<ScenarioSection
									scenario={state.scenario}
									loading={state.loading}
									deleteScenario={store.deleteScenario}
									editScenario={enterEditorMode}
								/>
							{:else if activeSidebarTab === 'solutions'}
								<SolutionsSection
									solutions={state.solutions}
									scenarioId={state.scenario?.id ?? null}
									selectedSolutionId={state.solution?.id ?? null}
									loadSolution={store.loadSolution}
								/>
							{:else}
								<JobsSection jobs={state.jobs} />
							{/if}
						</section>
					</div>
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
