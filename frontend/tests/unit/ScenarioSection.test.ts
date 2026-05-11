// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';

import ScenarioSection from '../../src/lib/components/ScenarioSection.svelte';
import type { Hospital, ScenarioPayload } from '../../src/lib/store';

const makeHospital = (overrides: Partial<Hospital> = {}): Hospital => ({
    id: 1,
    name: 'Hospital 1',
    lat_e6: 53100000,
    lng_e6: -8200000,
    display_lat_e6: 53100000,
    display_lng_e6: -8200000,
    snap_distance_m: 0,
    category: 'Hospital',
    subcategory: 'General',
    address: '1 Main St',
    eircode: 'D91TEST',
    demand: 3,
    lat: 53.1,
    lng: -8.2,
    display_lat: 53.1,
    display_lng: -8.2,
    ...overrides
});

const makeScenario = (): ScenarioPayload => ({
    id: 42,
    name: 'Scenario Alpha',
    description: 'Test scenario',
    vehicles: [
        { capacity: 10, quantity: 2 },
        { capacity: 20, quantity: -1 }
    ],
    depots: [
        makeHospital({
            id: 100,
            name: 'Main Depot',
            address: 'Depot Road',
            eircode: 'D01DEPOT',
            demand: 0
        })
    ],
    customers: [
        makeHospital({
            id: 200,
            name: 'Customer A',
            address: 'Customer Street',
            eircode: 'C01A',
            demand: 4
        }),
        makeHospital({
            id: 201,
            name: 'Customer B',
            address: 'Second Street',
            eircode: '',
            demand: 6
        })
    ]
});

describe('ScenarioSection', () => {
    it('shows the empty state when no scenario is provided', () => {
        render(ScenarioSection);

        expect(screen.getByText('No scenario selected.')).toBeInTheDocument();
    });

    it('shows the loading state when loading is true', () => {
        render(ScenarioSection, { props: { loading: true } });

        expect(screen.getByText('Loading scenario...')).toBeInTheDocument();
    });

    it('renders selected scenario name and counts', () => {
        render(ScenarioSection, {
            props: {
                scenario: makeScenario()
            }
        });

        expect(screen.getByRole('heading', { name: 'Scenario Alpha' })).toBeInTheDocument();
        expect(screen.getByText('1 depots')).toBeInTheDocument();
        expect(screen.getByText('2 customers')).toBeInTheDocument();
        expect(screen.getByText('Depots: 1')).toBeInTheDocument();
        expect(screen.getByText('Vehicles: 2')).toBeInTheDocument();
    });

    it('renders depot, customer, and vehicle details from props', () => {
        const { container } = render(ScenarioSection, {
            props: {
                scenario: makeScenario()
            }
        });

        const text = container.textContent ?? '';

        expect(text).toContain('Main Depot');
        expect(text).toContain('Depot Road');
        expect(text).toContain('D01DEPOT');

        expect(text).toContain('Customers (2)');
        expect(text).toContain('Customer A');
        expect(text).toContain('Customer Street');
        expect(text).toContain('C01A');
        expect(text).toContain('demand 4');

        expect(text).toContain('Customer B');
        expect(text).toContain('Second Street');
        expect(text).toContain('demand 6');

        expect(text).toContain('Vehicles (2)');
        expect(text).toContain('Pool 1');
        expect(text).toContain('capacity 10');
        expect(text).toContain('quantity 2');
        expect(text).toContain('Pool 2');
        expect(text).toContain('capacity 20');
        expect(text).toContain('unlimited');
    });
});