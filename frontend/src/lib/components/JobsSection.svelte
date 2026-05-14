<script lang="ts">
    import { jobStatusLabel, type SolverJobPayload, cancelJob } from '$lib/store';

    type Props = {
        jobs?: SolverJobPayload[];
    };

    let { jobs = [] }: Props = $props();

    let cancelJobIds: number[] = $state([]);

    const requestCancelJob = async (job: SolverJobPayload): Promise<void> => {
        if (cancelJobIds.includes(job.id)) {
            return;
        }

        cancelJobIds = [...cancelJobIds, job.id];

        try {
            await cancelJob(job.id);
        } catch (error) {
            console.error(`Failed to cancel job ${job.id}:`, error);
            cancelJobIds = cancelJobIds.filter((id) => id !== job.id);
        }
    };
</script>

<div class="grid gap-3">
    {#if jobs.length === 0}
        <p class="text-sm text-slate-600">No jobs yet.</p>
    {:else}
        <ul class="m-0 grid list-none gap-3 p-0">
            {#each jobs as job (job.id)}
                <li class="rounded-2xl border border-slate-200 bg-white p-3 shadow-lg shadow-slate-900/10">
                    <div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-600">
                        <strong class="wrap-break-words text-sm text-slate-900">
                            Job #{job.id}
                        </strong>

                        <span>Scenario: {job.scenario_id}</span>

                        <span
                            class={`inline-block rounded-full px-2 py-0.5 text-[11px] font-bold capitalize ${
                                job.status === 'finished'
                                    ? 'bg-green-100 text-green-800'
                                    : job.status === 'running'
                                      ? 'bg-blue-100 text-blue-800'
                                      : job.status === 'failed'
                                        ? 'bg-red-100 text-red-800'
                                        : job.status === 'cancelled'
                                          ? 'bg-amber-100 text-amber-800'
                                          : 'bg-slate-200 text-slate-900'
                            }`}
                        >
                            {jobStatusLabel(job.status)}
                        </span>

                        <span>Created: {job.created_at}</span>

                        {#if job.started_at}
                            <span>Started: {job.started_at}</span>
                        {/if}

                        {#if job.finished_at}
                            <span>Finished: {job.finished_at}</span>
                        {/if}

                        <span>
                            prep {job.preparation_ms}ms / solve {job.solver_ms}ms / results {job.results_ms}ms
                        </span>

                        <button
                            class="ml-auto h-7.5 cursor-pointer rounded-md border border-[#0f4c81] bg-[#0f4c81] px-3 text-xs text-white disabled:cursor-not-allowed disabled:opacity-55"
                            type="button"
                            onclick={() => requestCancelJob(job)}
                            hidden={job.status !== 'running' && job.status !== 'queued'}
                            disabled={cancelJobIds.includes(job.id)}
                        >
                            Cancel
                        </button>
                    </div>

                    <details class="mt-3 border-t border-slate-200 pt-2">
                        <summary class="cursor-pointer text-sm font-bold text-slate-900">
                            Details
                        </summary>

                        <div class="grid gap-1 pt-2 text-xs leading-5 text-slate-600">
                            <div>Name: {job.name ?? `Job #${job.id}`}</div>
                            <div>Method: {job.method}</div>

                            {#if job.solution_id !== undefined && job.solution_id !== null}
                                <div>Solution: {job.solution_id}</div>
                            {/if}

                            {#if job.options}
                                <pre class="m-0 max-w-full overflow-x-auto rounded-md bg-slate-50 p-2 text-[11px] leading-4 text-slate-700">{JSON.stringify(job.options, null, 2)}</pre>
                            {:else}
                                <div>Options: none</div>
                            {/if}
                        </div>
                    </details>

                    <details class="mt-2 border-t border-slate-200 pt-2">
                        <summary class="cursor-pointer text-sm font-bold text-slate-900">
                            Log ({job.log.length})
                        </summary>

                        {#if job.log.length > 0}
                            <ul class="m-0 grid list-none gap-2 pt-2 pl-0">
                                {#each job.log as entry (entry.timestamp + entry.message)}
                                    <li class="grid gap-1 rounded-md bg-slate-50 p-2 text-xs text-slate-600">
                                        <div class="flex flex-wrap items-center gap-2">
                                            <span class="break-all">{entry.timestamp}</span>
                                            <span
                                                class={`inline-block rounded-full px-2 py-0.5 text-[11px] font-bold capitalize ${
                                                    entry.level === 'error'
                                                        ? 'bg-red-100 text-red-800'
                                                        : entry.level === 'warning'
                                                          ? 'bg-amber-100 text-amber-800'
                                                          : entry.level === 'debug'
                                                            ? 'bg-slate-200 text-slate-800'
                                                            : 'bg-blue-100 text-blue-800'
                                                }`}
                                            >
                                                {entry.level}
                                            </span>
                                        </div>

                                        <div class="wrap-break-words leading-5 text-slate-700">
                                            {entry.message}
                                        </div>
                                    </li>
                                {/each}
                            </ul>
                        {:else}
                            <div class="pt-2 text-xs text-slate-600">No log entries.</div>
                        {/if}
                    </details>
                </li>
            {/each}
        </ul>
    {/if}
</div>