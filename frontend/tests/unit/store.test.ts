import { describe, expect, it } from 'vitest';

import {
	createInitialState,
	isHospitalLocation,
	jobStatusLabel,
	makeGeometryKey,
	type AppViewState
} from '../../src/lib/store';

describe('store helpers', () => {
	it('formats job status labels', () => {
		expect(jobStatusLabel('queued')).toBe('Queued');
		expect(jobStatusLabel('finished')).toBe('Finished');
	});

	it('validates hospital locations', () => {
		const valid = {
			id: 1,
			name: 'Test Hospital',
			lat: 53.1,
			lng: -8.2,
			lat_e6: 53100000,
			lng_e6: -82000000,
			display_lat: 53.1,
			display_lng: -8.2,
			display_lat_e6: 53100000,
			display_lng_e6: -82000000,
			category: 'General',
			subcategory: 'Regional',
			address: '1 Main St',
			eircode: 'D91TEST',
			demand: 3
		};

		expect(isHospitalLocation(valid)).toBe(true);
		expect(isHospitalLocation({ name: 'Missing fields' })).toBe(false);
	});

	it('makes correct geometry keys', () => {
		const num1 = 53123456;
		const num2 = -81234567;
		const num3 = 54123456;
		const num4 = -82123456;
		const expected = `${num1}_${num2}_${num3}_${num4}`;
		expect(makeGeometryKey(num1, num2, num3, num4)).toBe(expected);
	});

	it('creates correct initial state', () => {
		const state: AppViewState = createInitialState();
		expect(state).toEqual({
			scenario: null,
			scenarios: [],
			jobs: [],
			solution: null,
			solutions: [],
			loading: false,
			hospitals: [],
			error: null,
			geometries: new Map(),
			geometryVersion: 0
		});
	});
});
