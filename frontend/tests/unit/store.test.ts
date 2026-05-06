import { describe, expect, it } from 'vitest';

import { isHospitalLocation, jobStatusLabel } from '../../src/lib/store';

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
            demand: 3,
        };

        expect(isHospitalLocation(valid)).toBe(true);
        expect(isHospitalLocation({ name: 'Missing fields' })).toBe(false);
    });
});
