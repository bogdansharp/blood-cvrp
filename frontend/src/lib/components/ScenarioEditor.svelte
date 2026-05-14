<script lang="ts">
    import type { Hospital, ScenarioPayload, VehiclePool } from '$lib/store';

    type Props = {
        scenario?: ScenarioPayload | null;
        endEditing: (scenario: ScenarioPayload | null) => void;
    };

    let { scenario = null, endEditing }: Props = $props();

    const makeEmptyScenario = (): ScenarioPayload => ({
        id: 0,
        name: '',
        description: '',
        vehicles: [],
        depots: [],
        customers: []
    });

    const makeVehicle = (): VehiclePool => ({
        capacity: 60,
        quantity: -1
    });

    const makeHospital = (overrides: Partial<Hospital> = {}): Hospital => ({
        id: 0,
        name: '',
        lat_e6: 0,
        lng_e6: 0,
        display_lat_e6: null,
        display_lng_e6: null,
        snap_distance_m: 0,
        category: 'Hospital',
        subcategory: '',
        address: '',
        eircode: '',
        demand: 0,
        lat: 0,
        lng: 0,
        display_lat: 0,
        display_lng: 0,
        ...overrides
    });

    const cloneScenario = (value: ScenarioPayload | null): ScenarioPayload => {
        if (!value) {
            return makeEmptyScenario();
        }

        return {
            ...value,
            id: 0,
            name: `${value.name} copy`,
            description: `${value.description}`,
            vehicles: value.vehicles.map((vehicle) => ({ ...vehicle })),
            depots: value.depots.map((depot) => ({ ...depot })),
            customers: value.customers.map((customer) => ({ ...customer }))
        };
    };

    let draft: ScenarioPayload = $state(cloneScenario(scenario));
    let saving = $state(false);

    const addVehicle = () => {
        draft.vehicles = [...draft.vehicles, makeVehicle()];
    };

    const removeVehicle = (index: number) => {
        draft.vehicles = draft.vehicles.filter((_, itemIndex) => itemIndex !== index);
    };

    const addDepot = () => {
        draft.depots = [...draft.depots, makeHospital({ name: 'Depot', demand: 0 })];
    };

    const removeDepot = (index: number) => {
        draft.depots = draft.depots.filter((_, itemIndex) => itemIndex !== index);
    };

    const addCustomer = () => {
        draft.customers = [...draft.customers, makeHospital({ name: 'Customer', demand: 1 })];
    };

    const removeCustomer = (index: number) => {
        draft.customers = draft.customers.filter((_, itemIndex) => itemIndex !== index);
    };

    const verifyScenario = (scenario: ScenarioPayload): boolean => {
        if (!scenario.name.trim()) {
            alert('Scenario name is required.');
            return false;
        }

        if (scenario.vehicles.length === 0) {
            alert('At least one vehicle pool is required.');
            return false;
        }

        if (scenario.depots.length !== 1) {
            alert('A depot is required.');
            return false;
        }

        if (scenario.customers.length === 0) {
            alert('At least one customer is required.');
            return false;
        }

        return true;
    };

    const requestSave = async () => {
        if (!verifyScenario(draft)) {
            return;
        }
        try {
            saving = true;
            await endEditing(draft);
        } finally {
            saving = false;
        }
    };
</script>

<div class="grid gap-3">
    <div class="flex items-start justify-between gap-4">
        <div class="min-w-0">
            <p class="mb-1 text-xs uppercase tracking-[0.16em] text-slate-500">Scenario editor</p>
            <h2 class="m-0 wrap-break-words text-lg font-semibold text-slate-900">
                {scenario ? 'Edit as new scenario' : 'Create scenario'}
            </h2>
        </div>
    </div>

    <div class="grid gap-2 rounded-xl border border-slate-200 bg-white p-3">
        <label class="grid gap-1 text-sm text-slate-700">
            Name
            <input
                class="h-8 rounded-md border border-slate-300 px-2 text-sm text-slate-900"
                bind:value={draft.name}
            />
        </label>

        <label class="grid gap-1 text-sm text-slate-700">
            Description
            <textarea
                class="min-h-20 rounded-md border border-slate-300 px-2 py-1 text-sm text-slate-900"
                bind:value={draft.description}
            ></textarea>
        </label>
    </div>

    <details class="border-t border-slate-200 pt-3" open>
        <summary class="cursor-pointer list-none text-sm font-bold text-slate-900 outline-none">
            Vehicles ({draft.vehicles.length})
        </summary>

        <ul class="m-0 grid list-none gap-2 pt-3 pl-0">
            {#each draft.vehicles as vehicle, index}
                <li class="grid gap-2 rounded-xl border border-slate-200 bg-white p-2">
                    <div class="flex items-center justify-between gap-2">
                        <strong class="text-sm text-slate-900">Pool {index + 1}</strong>
                        <button
                            class="h-7 rounded-md border border-red-700 px-2 text-xs text-red-700 disabled:opacity-50 cursor-pointer"
                            type="button"
                            onclick={() => removeVehicle(index)}
                        >
                            Remove
                        </button>
                    </div>

                    <div class="grid grid-cols-3 gap-2">
                        <label class="grid gap-1 text-xs text-slate-600">
                            Capacity
                            <input
                                class="h-8 rounded-md border border-slate-300 px-2 text-sm text-slate-900 w-20"
                                type="number"
                                min="1"
                                bind:value={vehicle.capacity}
                            />
                        </label>

                        <label class="grid gap-1 text-xs text-slate-600">
                            Unlimited
                            <input
                                class="h-5 w-5 justify-self-center"
                                type="checkbox"
                                checked={vehicle.quantity === -1}
                                onchange={() => {
                                    if (vehicle.quantity === -1) {
                                        vehicle.quantity = 1;
                                    } else {
                                        vehicle.quantity = -1;
                                    }
                                }}
                            />
                        </label>

                        <label 
                            class="grid gap-1 text-xs text-slate-600" 
                            hidden={vehicle.quantity === -1}
                        >
                            Quantity
                            <input
                                class="h-8 rounded-md border border-slate-300 px-2 text-sm text-slate-900 w-20"
                                type="number"
                                bind:value={vehicle.quantity}
                                disabled={vehicle.quantity === -1}
                                min="1"
                            />
                        </label>
                    </div>
                </li>
            {/each}
        </ul>

        <button
            class="mt-2 h-7 rounded-md border border-[#0f4c81] bg-[#0f4c81] px-3 text-xs text-white cursor-pointer"
            type="button"
            onclick={addVehicle}
        >
            Add vehicle
        </button>
    </details>

    <details class="border-t border-slate-200 pt-3" open>
        <summary class="cursor-pointer list-none text-sm font-bold text-slate-900 outline-none">
            Depots ({draft.depots.length})
        </summary>

        <ul class="m-0 grid list-none gap-2 pt-3 pl-0">
            {#each draft.depots as depot, index}
                <li class="grid gap-2 rounded-xl border border-slate-200 bg-white p-2">
                    <div class="flex items-center justify-between gap-2">
                        <strong class="text-sm text-slate-900">Depot {index + 1}</strong>
                        <button
                            class="h-7 rounded-md border border-red-700 px-2 text-xs text-red-700 disabled:opacity-50 cursor-pointer"
                            type="button"
                            onclick={() => removeDepot(index)}
                            disabled={draft.depots.length <= 1}
                        >
                            Remove
                        </button>
                    </div>

                    <input class="h-8 rounded-md border border-slate-300 px-2 text-sm" placeholder="Name" bind:value={depot.name} />
                    <input class="h-8 rounded-md border border-slate-300 px-2 text-sm" placeholder="Address" bind:value={depot.address} />
                    <input class="h-8 rounded-md border border-slate-300 px-2 text-sm" placeholder="Eircode" bind:value={depot.eircode} />

                    <div class="grid grid-cols-2 gap-2">
                        <input class="h-8 rounded-md border border-slate-300 px-2 text-sm" type="number" placeholder="lat_e6" bind:value={depot.lat_e6} />
                        <input class="h-8 rounded-md border border-slate-300 px-2 text-sm" type="number" placeholder="lng_e6" bind:value={depot.lng_e6} />
                    </div>
                </li>
            {/each}
        </ul>

        <button
            class="mt-2 h-7 rounded-md border border-[#0f4c81] bg-[#0f4c81] px-3 text-xs text-white cursor-pointer"
            type="button"
            onclick={addDepot}
        >
            Add depot
        </button>
    </details>

    <details class="border-t border-slate-200 pt-3" open>
        <summary class="cursor-pointer list-none text-sm font-bold text-slate-900 outline-none">
            Customers ({draft.customers.length})
        </summary>

        <ul class="m-0 grid list-none gap-2 pt-3 pl-0">
            {#each draft.customers as customer, index}
                <li class="grid gap-2 rounded-xl border border-slate-200 bg-white p-2">
                    <div class="flex items-center justify-between gap-2">
                        <strong class="text-sm text-slate-900">Customer {index + 1}</strong>
                        <button
                            class="h-7 rounded-md border border-red-700 px-2 text-xs text-red-700 cursor-pointer"
                            type="button"
                            onclick={() => removeCustomer(index)}
                        >
                            Remove
                        </button>
                    </div>

                    <input class="h-8 rounded-md border border-slate-300 px-2 text-sm" placeholder="Name" bind:value={customer.name} />
                    <input class="h-8 rounded-md border border-slate-300 px-2 text-sm" placeholder="Address" bind:value={customer.address} />
                    <input class="h-8 rounded-md border border-slate-300 px-2 text-sm" placeholder="Eircode" bind:value={customer.eircode} />

                    <div class="grid grid-cols-3 gap-2">
                        <input class="h-8 rounded-md border border-slate-300 px-2 text-sm" type="number" placeholder="Demand" bind:value={customer.demand} />
                        <input class="h-8 rounded-md border border-slate-300 px-2 text-sm" type="number" placeholder="lat_e6" bind:value={customer.lat_e6} />
                        <input class="h-8 rounded-md border border-slate-300 px-2 text-sm" type="number" placeholder="lng_e6" bind:value={customer.lng_e6} />
                    </div>
                </li>
            {/each}
        </ul>

        <button
            class="mt-2 h-7 rounded-md border border-[#0f4c81] bg-[#0f4c81] px-3 text-xs text-white cursor-pointer"
            type="button"
            onclick={addCustomer}
        >
            Add customer
        </button>
    </details>

    <div class="flex flex-wrap gap-2 border-t border-slate-200 pt-3">
        <button
            class="h-7.5 rounded-md border border-[#0f4c81] bg-[#0f4c81] px-3 text-xs text-white disabled:cursor-not-allowed disabled:opacity-55 cursor-pointer"
            type="button"
            onclick={requestSave}
            disabled={saving}
        >
            Save
        </button>

        <button
            class="h-7.5 rounded-md border border-slate-400 bg-white px-3 text-xs text-slate-800 disabled:cursor-not-allowed disabled:opacity-55 cursor-pointer"
            type="button"
            onclick={() => endEditing(null)}
            disabled={saving}
        >
            Cancel
        </button>
    </div>
</div>