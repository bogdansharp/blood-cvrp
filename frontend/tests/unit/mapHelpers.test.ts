import { describe, expect, it } from 'vitest';

import { getBearingDegrees } from '../../src/lib/mapHelpers';

describe('map helpers', () => {
	it('calculates bearing north', () => {
		const bearing = getBearingDegrees([53, -8], [54, -8]);

		expect(bearing).toBeCloseTo(0, 1);
	});

	it('calculates bearing east', () => {
		const bearing = getBearingDegrees([53, -8], [53, -7]);

		expect(bearing).toBeGreaterThan(89);
		expect(bearing).toBeLessThan(91);
	});

	it('calculates bearing south', () => {
		const bearing = getBearingDegrees([53, -8], [52, -8]);

		expect(bearing).toBeGreaterThan(179);
		expect(bearing).toBeLessThan(181);
	});

	it('calculates bearing west', () => {
		const bearing = getBearingDegrees([53, -8], [53, -9]);

		expect(bearing).toBeGreaterThan(269);
		expect(bearing).toBeLessThan(271);
	});

	it('always returns a value from 0 inclusive to 360 exclusive', () => {
		const bearing = getBearingDegrees([53.331, -8.092], [51.898, -8.475]);

		expect(bearing).toBeGreaterThanOrEqual(0);
		expect(bearing).toBeLessThan(360);
	});
});
