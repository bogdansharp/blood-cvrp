import type { Hospital, HospitalLocation, ScenarioPayload } from '$lib/store';

export const toE6 = (value: number): number => Math.round(value * 1e6);

export const locationKey = (item: { lat_e6: number; lng_e6: number }): string =>
	`${item.lat_e6}_${item.lng_e6}`;

export const makeEmptyScenario = (): ScenarioPayload => ({
	id: 0,
	name: 'Custom Scenario',
	description: '',
	vehicles: [],
	depots: [],
	customers: []
});

export const cloneScenario = (scenario: ScenarioPayload | null): ScenarioPayload => {
	if (!scenario) {
		return makeEmptyScenario();
	}

	return {
		...scenario,
		id: 0,
		name: `${scenario.name} copy`,
		vehicles: scenario.vehicles.map((vehicle) => ({ ...vehicle })),
		depots: scenario.depots.map((depot) => ({ ...depot })),
		customers: scenario.customers.map((customer) => ({ ...customer }))
	};
};

export const makeHospitalFromLocation = (location: HospitalLocation): Hospital => ({
	...location,
	lat_e6: toE6(location.lat),
	lng_e6: toE6(location.lng),
	display_lat_e6: toE6(location.display_lat),
	display_lng_e6: toE6(location.display_lng),
	snap_distance_m: 0
});

export const makeHospitalFromSnappedPoint = (
	lat: number,
	lng: number,
	snappedLatE6: number,
	snappedLngE6: number,
	snapDistanceM: number
): Hospital => ({
	id: 0,
	name: '',
	lat_e6: toE6(lat),
	lng_e6: toE6(lng),
	display_lat_e6: snappedLatE6,
	display_lng_e6: snappedLngE6,
	snap_distance_m: snapDistanceM,
	category: 'Custom',
	subcategory: '',
	address: '',
	eircode: '',
	demand: 2,
	lat,
	lng,
	display_lat: snappedLatE6 / 1e6,
	display_lng: snappedLngE6 / 1e6
});
