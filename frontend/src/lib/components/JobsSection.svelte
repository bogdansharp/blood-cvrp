<script lang="ts">
    import { jobStatusLabel, type SolverJobPayload } from '$lib/store';

    type Props = {
        jobs?: SolverJobPayload[];
    };

    let { jobs = [] }: Props = $props();
</script>

<div class="jobs">
    {#if jobs.length === 0}
        <p class="status">No jobs yet.</p>
    {:else}
        <ul class="jobs-list">
            {#each jobs as job (job.id)}
                <li class="job-card">
                    <div class="job-row">
                        <strong>{job.name ?? `Job #${job.id}`}</strong>
                        <span class={`badge badge-${job.status}`}>{jobStatusLabel(job.status)}</span>
                    </div>
                    <div class="job-meta">Method: {job.method} | Scenario: {job.scenario_id}</div>
                    <div class="job-meta">Created: {job.created_at}</div>
                    {#if job.started_at}
                        <div class="job-meta">Started: {job.started_at}</div>
                    {/if}
                    {#if job.finished_at}
                        <div class="job-meta">Finished: {job.finished_at}</div>
                    {/if}
                    {#if job.solution_id !== undefined && job.solution_id !== null}
                        <div class="job-meta">Solution: {job.solution_id}</div>
                    {/if}
                    <div class="job-meta">
                        Timing: prep {job.preparation_ms}ms, solve {job.solver_ms}ms, results {job.results_ms}ms
                    </div>
                    {#if job.log.length > 0}
                        <details class="job-log">
                            <summary>Log ({job.log.length})</summary>
                            <ul>
                                {#each job.log as entry (entry.timestamp + entry.message)}
                                    <li>
                                        <span>{entry.timestamp}</span>
                                        <span class={`badge badge-${entry.level}`}>{entry.level}</span>
                                        <span>{entry.message}</span>
                                    </li>
                                {/each}
                            </ul>
                        </details>
                    {:else}
                        <div class="job-meta">Log: none</div>
                    {/if}
                </li>
            {/each}
        </ul>
    {/if}
</div>

<style>
    .jobs {
        display: grid;
        gap: 0.85rem;
    }

    .status {
        color: #475569;
        font-size: 0.95rem;
    }

    .jobs-list {
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        gap: 0.85rem;
    }

    .job-card {
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 16px;
        padding: 1rem;
        background: #ffffff;
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
    }

    .job-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 0.65rem;
    }

    .job-row strong {
        font-size: 1rem;
        color: #0f172a;
    }

    .job-meta {
        color: #475569;
        font-size: 0.9rem;
        line-height: 1.6;
    }

    .job-meta + .job-meta {
        margin-top: 0.35rem;
    }

    .job-log {
        margin-top: 0.75rem;
        border-top: 1px solid rgba(148, 163, 184, 0.2);
        padding-top: 0.75rem;
    }

    .job-log summary {
        cursor: pointer;
        color: #0f172a;
        font-weight: 700;
    }

    .job-log ul {
        list-style: none;
        padding: 0.75rem 0 0;
        margin: 0;
        display: grid;
        gap: 0.55rem;
    }

    .job-log li {
        display: grid;
        grid-template-columns: auto auto 1fr;
        gap: 0.5rem;
        align-items: center;
        color: #475569;
        font-size: 0.85rem;
    }

    .badge {
        display: inline-block;
        padding: 0.18rem 0.65rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: capitalize;
        background: #e2e8f0;
        color: #0f172a;
    }

    .badge-finished {
        background: #dcfce7;
        color: #166534;
    }

    .badge-running {
        background: #dbeafe;
        color: #1e40af;
    }

    .badge-failed {
        background: #fee2e2;
        color: #991b1b;
    }

    .badge-cancelled {
        background: #fef3c7;
        color: #92400e;
    }
</style>
