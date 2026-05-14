<script lang="ts">
    import { SOLVE_METHOD_LABELS, type SolutionPayload } from '$lib/store';

    type Props = {
        solutions?: SolutionPayload[];
        scenarioId?: number | null;
        selectedSolutionId?: number | null;
        loadSolution: (solutionId: number) => unknown | Promise<unknown>;
    };

    let {
        solutions = [],
        scenarioId = null,
        selectedSolutionId = null,
        loadSolution
    }: Props = $props();

    let visibleSolutions = $derived(
        scenarioId === null
            ? []
            : solutions.filter((solution) => solution.scenario_id === scenarioId)
    );

    const formatDateTime = (value: string): string => {
        return value.replace('T', ' ').replace(/\.\d+Z$/, '').replace(/Z$/, '');
    };

    const formatLimit = (seconds: number | null | undefined): string => {
        if (seconds === null || seconds === undefined) {
            return 'none';
        }

        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);

        return `${hours}h ${String(minutes).padStart(2, '0')}m`;
    };

    const formatOption = (value: string | boolean | null | undefined): string => {
        if (value === null || value === undefined) {
            return 'none';
        }

        if (typeof value === 'boolean') {
            return value ? 'yes' : 'no';
        }

        return value.toLowerCase().replaceAll('_', ' ');
    };
</script>

<div class="grid gap-3">
    {#if scenarioId === null}
        <p class="text-sm text-slate-600">No scenario selected.</p>
    {:else if visibleSolutions.length === 0}
        <p class="text-sm text-slate-600">No solutions for this scenario yet.</p>
    {:else}
        <ul class="m-0 grid list-none gap-2 p-0">
            {#each visibleSolutions as solution (solution.id)}
                <li>
                    <button
                        class={`grid w-full cursor-pointer gap-1 rounded-xl border p-3 text-left shadow-sm ${
                            selectedSolutionId === solution.id
                                ? 'border-[#0f4c81] bg-blue-50'
                                : 'border-slate-200 bg-white'
                        }`}
                        type="button"
                        onclick={() => loadSolution(solution.id)}
                    >
                        <div class="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                            <strong class="text-sm text-slate-900">Solution #{solution.id}</strong>

                            <span class="rounded-full bg-slate-200 px-2 py-0.5 text-[11px] font-bold text-slate-800">
                                {SOLVE_METHOD_LABELS[solution.method] ?? solution.method}
                            </span>
                        </div>

                        <div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-600">
                            <span>{(solution.total_distance / 1000).toFixed(2)} km</span>
                            <span>{Math.round(solution.total_travel_time / 60)} min</span>
                            <span>{solution.routes.length} routes</span>

                            {#if solution.options?.cost_limit !== undefined && solution.options.cost_limit !== null}
                                <span>limit: {formatLimit(solution.options.cost_limit)}</span>
                            {/if}

                            {#if solution.method === 'ortools'}
                                <span>balance: {formatOption(solution.options?.or_balance_routes)}</span>
                                <span>first: {formatOption(solution.options?.or_first_solution_strategy)}</span>
                                <span>search: {formatOption(solution.options?.or_local_search_metaheuristic)}</span>
                            {/if}

                            {#if solution.method === 'clarke_wright_savings'}
                                <span>search: {formatOption(solution.options?.clarke_local_search)}</span>
                            {/if}
                        </div>

                        <div class="wrap-break-words text-xs text-slate-500">
                            Created: {formatDateTime(solution.created_at)}
                        </div>
                    </button>
                </li>
            {/each}
        </ul>
    {/if}
</div>