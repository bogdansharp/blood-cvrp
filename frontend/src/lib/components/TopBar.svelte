<svelte:options runes={false} />

<script lang="ts">
	import {
		CLARKE_WRIGHT_LOCAL_SEARCH_LABELS,
		OR_FIRST_SOLUTION_STRATEGY_LABELS,
		OR_LOCAL_SEARCH_METAHEURISTIC_LABELS,
		SOLVE_METHOD_LABELS,
		type AppViewState,
		type ClarkeWrightLocalSearch,
		type ORFirstSolutionStrategy,
		type ORLocalSearchMetaheuristic,
		type SolveMethod
	} from '$lib/store';

	export let state: AppViewState;

	export let selectedMethod: SolveMethod;
	export let orLocalSearch: ORLocalSearchMetaheuristic;
	export let orFirstSolution: ORFirstSolutionStrategy;
	export let orBalanceRoutes: boolean;
	export let clarkeLocalSearch: ClarkeWrightLocalSearch;
	export let timeLimitHours: number;
	export let editorMode = false;

	export let onScenarioChange: (scenarioId: number | null) => void;
	export let onAddScenario: () => void;
	export let onSolve: () => void;

	const defaultSolveMethod: SolveMethod = 'clarke_wright_savings';

	const handleScenarioChange = (event: Event) => {
		const rawValue = (event.target as HTMLSelectElement).value;

		if (!rawValue) {
			onScenarioChange(null);
			return;
		}

		const value = Number(rawValue);

		if (Number.isNaN(value)) {
			onScenarioChange(null);
			return;
		}

		selectedMethod = defaultSolveMethod;
		onScenarioChange(value);
	};
</script>

<header
	class="z-20 grid gap-2 border-b border-neutral-300 bg-white p-2 min-[821px]:grid-cols-[180px_minmax(0,1fr)] min-[821px]:items-start min-[821px]:gap-3 min-[821px]:px-3"
>
	<div class="min-w-0">
		<h1 class="m-0 text-base leading-tight font-semibold min-[821px]:text-lg">Blood CVRP App</h1>

		{#if state.error}
			<p
				class="min-[821px]:wrap-break-words m-0 text-xs leading-tight text-red-700 min-[821px]:max-w-45"
			>
				{state.error}
			</p>
		{/if}
	</div>

	<div
		class="grid min-w-0 gap-2 min-[821px]:flex min-[821px]:flex-row-reverse min-[821px]:flex-wrap min-[821px]:items-end min-[821px]:gap-2"
	>
		<div
			class="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-end gap-2 min-[520px]:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)_auto] min-[821px]:flex min-[821px]:min-w-0 min-[821px]:flex-wrap min-[821px]:items-end min-[821px]:justify-end min-[821px]:gap-2"
		>
			<div class="grid min-w-0 gap-1 min-[821px]:w-55">
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

					{#each state.scenarios as scenario (scenario.id)}
						<option value={scenario.id} selected={state.scenario?.id === scenario.id}>
							{scenario.name}
						</option>
					{/each}
				</select>
			</div>

			<button
				class="h-7.5 cursor-pointer rounded-md border border-[#0f812a] bg-[#0f812a] px-2.5 text-xs text-white disabled:cursor-not-allowed disabled:opacity-55"
				type="button"
				onclick={onAddScenario}
				disabled={state.loading || editorMode}
			>
				+
			</button>

			<div class="col-span-2 grid min-w-0 gap-1 min-[520px]:col-span-1 min-[821px]:w-45">
				<label class="text-[11px] leading-none text-neutral-600" for="method-select">
					Method
				</label>

				<select
					class="h-7.5 w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950"
					id="method-select"
					bind:value={selectedMethod}
					disabled={editorMode}
				>
					{#each Object.entries(SOLVE_METHOD_LABELS) as [key, label] (key)}
						<option value={key}>{label}</option>
					{/each}
				</select>
			</div>

			<button
				class="col-span-2 h-7.5 w-full cursor-pointer rounded-md border border-[#0f4c81] bg-[#0f4c81] px-4 text-xs text-white disabled:cursor-not-allowed disabled:opacity-55 min-[520px]:col-span-1 min-[821px]:w-auto"
				type="button"
				onclick={onSolve}
				disabled={state.loading || !state.scenario || editorMode}
			>
				Solve
			</button>
		</div>

		<div
			class="grid min-w-0 grid-cols-1 gap-2 min-[520px]:grid-cols-2 min-[821px]:flex min-[821px]:min-w-0 min-[821px]:flex-wrap min-[821px]:items-end min-[821px]:justify-end min-[821px]:gap-2"
		>
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
					disabled={editorMode}
				/>
			</div>

			{#if selectedMethod === 'ortools'}
				<label
					class="flex h-7.5 items-center gap-2 rounded-md border border-neutral-300 px-2 text-xs text-neutral-700 min-[821px]:self-end"
				>
					<input
						type="checkbox"
						class="h-4 w-4"
						bind:checked={orBalanceRoutes}
						disabled={editorMode}
					/>
					Balance
				</label>

				<div class="grid min-w-0 gap-1 min-[821px]:w-42.5">
					<label class="text-[11px] leading-none text-neutral-600" for="or-first-solution-select">
						First solution
					</label>

					<select
						class="h-7.5 w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950"
						id="or-first-solution-select"
						bind:value={orFirstSolution}
						disabled={editorMode}
					>
						{#each Object.entries(OR_FIRST_SOLUTION_STRATEGY_LABELS) as [key, label] (key)}
							<option value={key}>{label}</option>
						{/each}
					</select>
				</div>

				<div class="grid min-w-0 gap-1 min-[821px]:w-40">
					<label class="text-[11px] leading-none text-neutral-600" for="or-local-search-select">
						Local search
					</label>

					<select
						class="h-7.5 w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950"
						id="or-local-search-select"
						bind:value={orLocalSearch}
						disabled={editorMode}
					>
						{#each Object.entries(OR_LOCAL_SEARCH_METAHEURISTIC_LABELS) as [key, label] (key)}
							<option value={key}>{label}</option>
						{/each}
					</select>
				</div>
			{/if}

			{#if selectedMethod === 'clarke_wright_savings'}
				<div class="grid min-w-0 gap-1 min-[821px]:w-40">
					<label class="text-[11px] leading-none text-neutral-600" for="clarke-local-search-select">
						Clarke local search
					</label>

					<select
						class="h-7.5 w-full min-w-0 rounded-md border border-neutral-400 bg-white px-2 text-xs text-neutral-950"
						id="clarke-local-search-select"
						bind:value={clarkeLocalSearch}
						disabled={editorMode}
					>
						{#each Object.entries(CLARKE_WRIGHT_LOCAL_SEARCH_LABELS) as [key, label] (key)}
							<option value={key}>{label}</option>
						{/each}
					</select>
				</div>
			{/if}
		</div>
	</div>
</header>
