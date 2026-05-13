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
                <li class="rounded-2xl border border-slate-200 bg-white p-4 shadow-lg shadow-slate-900/10">
                    <div class="mb-2 flex items-start justify-between gap-3">
                        <strong class="min-w-0 wrap-break-words text-sm font-semibold text-slate-900">
                            {job.name ?? `Job #${job.id}`}
                        </strong>
                    </div>

                    <div class="mb-2 flex flex-wrap items-center gap-2">
                        <span
                            class={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold capitalize ${
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

                        <button
                            class="h-7.5 rounded-md border border-[#0f4c81] bg-[#0f4c81] px-3 text-xs text-white disabled:cursor-not-allowed disabled:opacity-55"
                            type="button"
                            onclick={() => requestCancelJob(job)}
                            hidden={job.status !== 'running' && job.status !== 'queued'}
                            disabled={cancelJobIds.includes(job.id)}
                        >
                            Cancel
                        </button>
                    </div>

                    <div class="grid gap-1 text-sm leading-6 text-slate-600">
                        <div>Method: {job.method} | Scenario: {job.scenario_id}</div>
                        <div>Created: {job.created_at}</div>

                        {#if job.started_at}
                            <div>Started: {job.started_at}</div>
                        {/if}

                        {#if job.finished_at}
                            <div>Finished: {job.finished_at}</div>
                        {/if}

                        {#if job.solution_id !== undefined && job.solution_id !== null}
                            <div>Solution: {job.solution_id}</div>
                        {/if}

                        <div>
                            Timing: prep {job.preparation_ms}ms, solve {job.solver_ms}ms,
                            results {job.results_ms}ms
                        </div>
                    </div>

                    {#if job.log.length > 0}
                        <details class="mt-3 border-t border-slate-200 pt-3">
                            <summary class="cursor-pointer text-sm font-bold text-slate-900">
                                Log ({job.log.length})
                            </summary>

                            <ul class="m-0 grid list-none gap-2 pt-3 pl-0">
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
                        </details>
                    {:else}
                        <div class="mt-2 text-sm leading-6 text-slate-600">Log: none</div>
                    {/if}
                </li>
            {/each}
        </ul>
    {/if}
</div>