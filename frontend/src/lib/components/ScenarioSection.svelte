<script lang="ts">
    import { type ScenarioPayload } from '$lib/store';

    type Props = {
        scenario?: ScenarioPayload | null;
        loading?: boolean;
        deleteScenario: (scenarioId: number) => void | Promise<void>;
    };

    let { scenario = null, loading = false, deleteScenario }: Props = $props();
    let deleteInProgress: boolean = $state(false);

    const requestDeleteScenario = async (scenarioId: number): Promise<void> => {
        try {
            deleteInProgress = true;
            await deleteScenario(scenarioId);
        } catch (error) {
            console.error(`Failed to delete scenario ${scenarioId}:`, error);
        } finally {
            deleteInProgress = false;
        }
    };
</script>

<div class="grid gap-3">
    {#if loading}
        <p class="text-sm text-slate-600">Loading scenario...</p>
    {:else if !scenario}
        <p class="text-sm text-slate-600">No scenario selected.</p>
    {:else}
        <div class="flex items-center justify-between gap-4">
            <div class="min-w-0">
                <p class="mb-1 text-xs uppercase tracking-[0.16em] text-slate-500">Scenario</p>
                <h2 class="m-0 wrap-break-words text-lg font-semibold text-slate-900">
                    {scenario.name}
                </h2>
            </div>

            <div class="grid shrink-0 gap-1 text-right text-sm text-slate-600">
                <span>{scenario.depots.length} depots</span>
                <span>{scenario.customers.length} customers</span>
            </div>
        </div>

        <div class="flex flex-wrap gap-2 text-sm text-slate-700">
            <span class="rounded-full bg-indigo-50 px-3 py-1 text-indigo-800">
                Depots: {scenario.depots.length}
            </span>
            <span class="rounded-full bg-indigo-50 px-3 py-1 text-indigo-800">
                Vehicles: {scenario.vehicles.length}
            </span>
        </div>

        <div class="flex flex-wrap gap-2">
            <button
                class="h-7.5 cursor-pointer rounded-md border border-[#0f4c81] bg-[#0f4c81] px-3 text-xs text-white disabled:cursor-not-allowed disabled:opacity-55"
                type="button"
                onclick={() => requestDeleteScenario(scenario.id)}
                disabled={deleteInProgress}
            >
                Delete
            </button>

            <button
                class="h-7.5 cursor-pointer rounded-md border border-[#0f4c81] bg-[#0f4c81] px-3 text-xs text-white disabled:cursor-not-allowed disabled:opacity-55"
                type="button"
                disabled={true}
            >
                Edit
            </button>
        </div>

        <div class="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p class="mb-2 font-bold text-slate-900">Depots</p>

            <ul class="m-0 grid list-none gap-2 p-0">
                {#each scenario.depots as depot}
                    <li class="grid gap-0.5 rounded-xl border border-slate-200 bg-white p-2">
                        <strong class="wrap-break-words text-sm text-slate-900">{depot.name}</strong>
                        <span class="wrap-break-words text-sm text-slate-600">
                            {depot.address}{depot.eircode ? ` (${depot.eircode})` : ''}
                        </span>
                    </li>
                {/each}
            </ul>
        </div>

        <details class="border-t border-slate-200 pt-3">
            <summary class="cursor-pointer list-none text-sm font-bold text-slate-900 outline-none">
                Customers ({scenario.customers.length})
            </summary>

            <ul class="m-0 grid list-none gap-2 pt-3 pl-0">
                {#each scenario.customers as customer}
                    <li class="grid gap-0.5 rounded-xl border border-slate-200 bg-white p-2">
                        <strong class="wrap-break-words text-sm text-slate-900">{customer.name}</strong>
                        <span class="wrap-break-words text-sm text-slate-600">
                            {customer.address}{customer.eircode ? ` (${customer.eircode})` : ''} ·
                            demand {customer.demand}
                        </span>
                    </li>
                {/each}
            </ul>
        </details>

        <details class="border-t border-slate-200 pt-3">
            <summary class="cursor-pointer list-none text-sm font-bold text-slate-900 outline-none">
                Vehicles ({scenario.vehicles.length})
            </summary>

            <ul class="m-0 grid list-none gap-2 pt-3 pl-0">
                {#each scenario.vehicles as pool, index}
                    <li class="grid gap-0.5 rounded-xl border border-slate-200 bg-white p-2">
                        <strong class="text-sm text-slate-900">Pool {index + 1}</strong>
                        <span class="text-sm text-slate-600">
                            capacity {pool.capacity}, quantity {pool.quantity === -1
                                ? 'unlimited'
                                : pool.quantity}
                        </span>
                    </li>
                {/each}
            </ul>
        </details>
    {/if}
</div>