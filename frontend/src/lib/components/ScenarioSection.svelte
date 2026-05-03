<script lang="ts">
    import type { ScenarioPayload } from '$lib/store';

    type Props = {
        scenario?: ScenarioPayload | null;
        loading?: boolean;
    };

    let { scenario = null, loading = false }: Props = $props();
</script>

<div class="scenario">
    {#if loading}
        <p class="status">Loading scenario...</p>
    {:else if !scenario}
        <p class="status">No scenario selected.</p>
    {:else}
        <div class="scenario-header">
            <div>
                <p class="label">Scenario</p>
                <h2>{scenario.name}</h2>
            </div>
            <div class="pillar">
                <span>{scenario.depots.length} depots</span>
                <span>{scenario.customers.length} customers</span>
            </div>
        </div>

        <div class="scenario-summary">
            <span class="summary-item">Depots: {scenario.depots.length}</span>
            <span class="summary-item">Vehicles: {scenario.vehicles.length}</span>
        </div>

        <div class="section-block">
            <p class="section-title">Depots</p>
            <ul class="scenario-list">
                {#each scenario.depots as depot}
                    <li>
                        <strong>{depot.name}</strong>
                        <span class="scenario-meta">
                            {depot.address}{depot.eircode ? ` (${depot.eircode})` : ''}
                        </span>
                    </li>
                {/each}
            </ul>
        </div>

        <details class="scenario-details">
            <summary>Customers ({scenario.customers.length})</summary>
            <ul class="scenario-list">
                {#each scenario.customers as customer}
                    <li>
                        <strong>{customer.name}</strong>
                        <span class="scenario-meta">
                            {customer.address}{customer.eircode ? ` (${customer.eircode})` : ''} · demand {customer.demand}
                        </span>
                    </li>
                {/each}
            </ul>
        </details>

        <details class="scenario-details">
            <summary>Vehicles ({scenario.vehicles.length})</summary>
            <ul class="scenario-list">
                {#each scenario.vehicles as pool, index}
                    <li>
                        <strong>Pool {index + 1}</strong>
                        <span class="scenario-meta">
                            capacity {pool.capacity}, quantity {pool.quantity === -1 ? 'unlimited' : pool.quantity}
                        </span>
                    </li>
                {/each}
            </ul>
        </details>
    {/if}
</div>

<style>
    .scenario {
        display: grid;
        gap: 0.85rem;
    }

    .status {
        color: #475569;
        font-size: 0.95rem;
    }

    .scenario-header {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: center;
    }

    .label {
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-size: 0.75rem;
        color: #64748b;
        margin-bottom: 0.25rem;
    }

    h2 {
        margin: 0;
        font-size: 1.15rem;
        color: #0f172a;
    }

    .pillar {
        display: grid;
        gap: 0.35rem;
        text-align: right;
        font-size: 0.9rem;
        color: #475569;
    }

    .scenario-summary {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        font-size: 0.95rem;
        color: #334155;
    }

    .summary-item {
        background: #eef2ff;
        color: #3730a3;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
    }

    .section-block {
        padding: 0.85rem 0.95rem;
        background: #f8fafc;
        border-radius: 14px;
        border: 1px solid rgba(148, 163, 184, 0.2);
    }

    .section-title {
        margin: 0 0 0.65rem;
        font-weight: 700;
        color: #0f172a;
    }

    .scenario-list {
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        gap: 0.55rem;
    }

    .scenario-list li {
        display: grid;
        gap: 0.15rem;
        padding: 0.55rem;
        border-radius: 12px;
        background: #ffffff;
        border: 1px solid rgba(148, 163, 184, 0.16);
    }

    .scenario-meta {
        color: #475569;
        font-size: 0.875rem;
    }

    .scenario-details {
        margin-top: 0.75rem;
        border-top: 1px solid rgba(148, 163, 184, 0.18);
        padding-top: 0.9rem;
    }

    .scenario-details summary {
        cursor: pointer;
        color: #0f172a;
        font-weight: 700;
        font-size: 0.98rem;
        list-style: none;
        outline: none;
    }
</style>
