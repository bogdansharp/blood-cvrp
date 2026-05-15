<script lang="ts">
	import type { ScenarioPayload, VehiclePool } from '$lib/store';

	type Props = {
		draft: ScenarioPayload;
		addingDepot: boolean;
		setDraft: (draft: ScenarioPayload) => void;
		startDepotSelection: () => void;
		cancelDepotSelection: () => void;
		endEditing: (scenario: ScenarioPayload | null) => void | Promise<void>;
	};

	let {
		draft,
		addingDepot,
		setDraft,
		startDepotSelection,
		cancelDepotSelection,
		endEditing
	}: Props = $props();

	let saving = $state(false);

	const makeVehicle = (): VehiclePool => ({
		capacity: 60,
		quantity: -1
	});

	const updateScenario = (patch: Partial<ScenarioPayload>) => {
		setDraft({ ...draft, ...patch });
	};

	const addVehicle = () => {
		updateScenario({ vehicles: [...draft.vehicles, makeVehicle()] });
	};

	const removeVehicle = (index: number) => {
		updateScenario({
			vehicles: draft.vehicles.filter((_, itemIndex) => itemIndex !== index)
		});
	};

	const updateVehicle = (index: number, patch: Partial<VehiclePool>) => {
		updateScenario({
			vehicles: draft.vehicles.map((vehicle, itemIndex) =>
				itemIndex === index ? { ...vehicle, ...patch } : vehicle
			)
		});
	};

	const removeDepot = (index: number) => {
		updateScenario({
			depots: draft.depots.filter((_, itemIndex) => itemIndex !== index)
		});
	};

	const updateDepotName = (index: number, name: string) => {
		updateScenario({
			depots: draft.depots.map((depot, itemIndex) =>
				itemIndex === index ? { ...depot, name } : depot
			)
		});
	};

	const removeCustomer = (index: number) => {
		updateScenario({
			customers: draft.customers.filter((_, itemIndex) => itemIndex !== index)
		});
	};

	const updateCustomer = (index: number, patch: { name?: string; demand?: number }) => {
		updateScenario({
			customers: draft.customers.map((customer, itemIndex) =>
				itemIndex === index ? { ...customer, ...patch } : customer
			)
		});
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
			alert('Select one depot on the map.');
			return false;
		}

		if (scenario.customers.length === 0) {
			alert('Select at least one customer on the map.');
			return false;
		}

		for (let i = 0; i < scenario.customers.length; i++) {
			if (scenario.customers[i].demand <= 0) {
				const name = scenario.customers[i].name || `#${i + 1}`;
				alert(`Customer ${name} has invalid demand.`);
				return false;
			}
		}

		return true;
	};

	const getDefaultCustomerName = (
		customer: { name: string; category: string },
		index: number
	): string => {
		if (customer.name.trim()) {
			return customer.name.trim();
		}

		return customer.category === 'Custom' ? `Custom #${index + 1}` : `Customer ${index + 1}`;
	};

	const prepareScenarioForSave = (scenario: ScenarioPayload): ScenarioPayload => ({
		...scenario,
		customers: scenario.customers.map((customer, index) => ({
			...customer,
			name: getDefaultCustomerName(customer, index)
		})),
		depots: scenario.depots.map((depot, index) => ({
			...depot,
			name: depot.name.trim() || `Depot ${index + 1}`
		}))
	});

	const requestSave = async () => {
		const scenarioToSave = prepareScenarioForSave(draft);

		if (!verifyScenario(scenarioToSave)) {
			return;
		}

		try {
			saving = true;
			await endEditing(scenarioToSave);
		} finally {
			saving = false;
		}
	};
</script>

<div class="grid gap-3">
	<div class="min-w-0">
		<p class="mb-1 text-xs tracking-[0.16em] text-slate-500 uppercase">Scenario editor</p>
		<input
			class="wrap-break-words m-0 text-lg font-semibold text-slate-900 focus-visible:outline-none"
			value={draft.name}
			oninput={(event) => updateScenario({ name: event.currentTarget.value })}
		/>

		<div class="mt-2 grid gap-2">
			<label class="grid gap-1 text-[11px] text-slate-700">
				Description
				<textarea
					class="min-h-20 rounded-md border border-slate-300 px-2 py-1 text-sm text-slate-900"
					value={draft.description ?? ''}
					oninput={(event) => updateScenario({ description: event.currentTarget.value })}
				></textarea>
			</label>
		</div>
	</div>

	<div class="flex flex-wrap gap-2 border-t border-slate-200 pt-3">
		<button
			class="h-7.5 cursor-pointer rounded-md border border-[#0f812a] bg-[#0f812a] px-3 text-xs text-white disabled:cursor-not-allowed disabled:opacity-55"
			type="button"
			onclick={requestSave}
			disabled={saving}
		>
			Save
		</button>

		<button
			class="h-7.5 cursor-pointer rounded-md border border-red-700 bg-white px-3 text-xs text-red-700 disabled:cursor-not-allowed disabled:opacity-55"
			type="button"
			onclick={() => endEditing(null)}
			disabled={saving}
		>
			Cancel
		</button>
	</div>

	<div class="rounded-xl border border-blue-200 bg-blue-50 p-2 text-sm text-blue-900">
		Click grey hospitals on the map to add customers. Click Select depot”, then click the depot
		location.
	</div>

	<details class="border-t border-slate-200 pt-3">
		<summary class="cursor-pointer list-none text-sm font-bold text-slate-900 outline-none">
			Vehicles ({draft.vehicles.length})
		</summary>

		<ul class="m-0 grid list-none gap-2 pt-3 pl-0">
			{#each draft.vehicles as vehicle, index (index)}
				<li class="grid gap-2 rounded-xl border border-slate-200 bg-white p-2">
					<div class="flex items-center justify-between gap-2">
						<strong class="text-sm text-slate-900">Pool {index + 1}</strong>
						<button
							class="h-7 cursor-pointer rounded-md border border-red-700 px-2 text-xs text-red-700 disabled:opacity-50"
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
								class="h-8 w-20 rounded-md border border-slate-300 px-2 text-sm text-slate-900"
								type="number"
								min="1"
								value={vehicle.capacity}
								oninput={(event) =>
									updateVehicle(index, { capacity: Number(event.currentTarget.value) })}
							/>
						</label>

						<label class="grid gap-1 text-xs text-slate-600">
							Unlimited
							<input
								class="h-5 w-5 justify-self-center"
								type="checkbox"
								checked={vehicle.quantity === -1}
								onchange={() =>
									updateVehicle(index, { quantity: vehicle.quantity === -1 ? 1 : -1 })}
							/>
						</label>

						<label class="grid gap-1 text-xs text-slate-600" hidden={vehicle.quantity === -1}>
							Quantity
							<input
								class="h-8 w-20 rounded-md border border-slate-300 px-2 text-sm text-slate-900"
								type="number"
								min="1"
								value={vehicle.quantity === -1 ? 1 : vehicle.quantity}
								oninput={(event) =>
									updateVehicle(index, { quantity: Number(event.currentTarget.value) })}
							/>
						</label>
					</div>
				</li>
			{/each}
		</ul>

		<button
			class="mt-2 h-7 cursor-pointer rounded-md border border-[#0f4c81] bg-[#0f4c81] px-3 text-xs text-white"
			type="button"
			onclick={addVehicle}
		>
			Add vehicle
		</button>
	</details>

	<details class="border-t border-slate-200 pt-3">
		<summary class="cursor-pointer list-none text-sm font-bold text-slate-900 outline-none">
			Depot ({draft.depots.length})
		</summary>

		<ul class="m-0 grid list-none gap-2 pt-3 pl-0">
			{#each draft.depots as depot, index (`${depot.lat}-${depot.lng}-${index}`)}
				<li class="grid gap-2 rounded-xl border border-slate-200 bg-white p-2">
					<div class="flex items-center justify-between gap-2">
						<input
							class="min-w-0 flex-1 bg-transparent p-0 text-sm font-bold text-slate-900 outline-none"
							value={depot.name || `Depot ${index + 1}`}
							oninput={(event) => updateDepotName(index, event.currentTarget.value)}
						/>

						<button
							class="h-7 cursor-pointer rounded-md border border-red-700 px-2 text-xs text-red-700"
							type="button"
							onclick={() => removeDepot(index)}
						>
							Remove
						</button>
					</div>

					<span class="wrap-break-words text-xs text-slate-600">
						{depot.address}{depot.eircode ? ` ${depot.eircode}` : ''}
					</span>
				</li>
			{/each}
		</ul>

		<div class="mt-2 flex flex-wrap gap-2">
			<button
				class={`h-7 cursor-pointer rounded-md border px-3 text-xs text-white ${
					addingDepot ? 'border-[#b23b00] bg-[#b23b00]' : 'border-[#0f4c81] bg-[#0f4c81]'
				}`}
				type="button"
				onclick={startDepotSelection}
				disabled={addingDepot}
			>
				{addingDepot ? 'Click depot on map' : 'Select depot'}
			</button>

			{#if addingDepot}
				<button
					class="h-7 cursor-pointer rounded-md border border-slate-400 bg-white px-3 text-xs text-slate-800"
					type="button"
					onclick={cancelDepotSelection}
				>
					Cancel depot selection
				</button>
			{/if}
		</div>
	</details>

	<details class="border-t border-slate-200 pt-3">
		<summary class="cursor-pointer list-none text-sm font-bold text-slate-900 outline-none">
			Customers ({draft.customers.length})
		</summary>

		<ul class="m-0 grid list-none gap-2 pt-3 pl-0">
			{#each draft.customers as customer, index (`${customer.lat}-${customer.lng}-${index}`)}
				<li class="grid gap-2 rounded-xl border border-slate-200 bg-white p-2">
					<div class="flex items-center justify-between gap-2">
						<input
							class="min-w-0 flex-1 bg-transparent p-0 text-sm font-bold text-slate-900 outline-none"
							value={getDefaultCustomerName(customer, index)}
							oninput={(event) => updateCustomer(index, { name: event.currentTarget.value })}
						/>

						<button
							class="h-7 cursor-pointer rounded-md border border-red-700 px-2 text-xs text-red-700"
							type="button"
							onclick={() => removeCustomer(index)}
						>
							Remove
						</button>
					</div>

					<input
						class="h-8 rounded-md border border-slate-300 px-2 text-sm"
						type="number"
						min="0"
						placeholder="Demand"
						value={customer.demand}
						oninput={(event) =>
							updateCustomer(index, { demand: Number(event.currentTarget.value) })}
					/>

					<span class="wrap-break-words text-xs text-slate-600">
						{customer.address}{customer.eircode ? ` ${customer.eircode}` : ''}
					</span>
				</li>
			{/each}
		</ul>
	</details>
</div>
