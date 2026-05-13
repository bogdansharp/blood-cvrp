// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi, afterEach } from 'vitest';

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

const renderScenarioSection = (props = {}) => {
    return render(ScenarioSection, {
        props: {
            deleteScenario: vi.fn(),
            ...props
        }
    });
};

describe('ScenarioSection', () => {
    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
    });

    it('shows the empty state when no scenario is provided', () => {
        renderScenarioSection();

        expect(screen.getByText('No scenario selected.')).toBeInTheDocument();
    });

    it('shows the loading state when loading is true', () => {
        renderScenarioSection({ loading: true });

        expect(screen.getByText('Loading scenario...')).toBeInTheDocument();
    });

    it('renders selected scenario name and counts', () => {
        renderScenarioSection({
            scenario: makeScenario()
        });

        expect(screen.getByRole('heading', { name: 'Scenario Alpha' })).toBeInTheDocument();
        expect(screen.getByText('1 depots')).toBeInTheDocument();
        expect(screen.getByText('2 customers')).toBeInTheDocument();
        expect(screen.getByText('Depots: 1')).toBeInTheDocument();
        expect(screen.getByText('Vehicles: 2')).toBeInTheDocument();
    });

    it('renders depot, customer, and vehicle details from props', () => {
        const { container } = renderScenarioSection({
            scenario: makeScenario()
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

    it('calls deleteScenario with selected scenario id', async () => {
        const deleteScenario = vi.fn().mockResolvedValue(undefined);

        renderScenarioSection({
            scenario: makeScenario(),
            deleteScenario
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));

        expect(deleteScenario).toHaveBeenCalledWith(42);
    });

    it('disables delete button while delete is in progress', async () => {
        let resolveDelete: () => void = () => undefined;

        const deleteScenario = vi.fn(
            () =>
                new Promise<void>((resolve) => {
                    resolveDelete = resolve;
                })
        );

        renderScenarioSection({
            scenario: makeScenario(),
            deleteScenario
        });

        const button = screen.getByRole('button', { name: 'Delete' });

        await fireEvent.click(button);

        await waitFor(() => {
            expect(button).toBeDisabled();
        });

        resolveDelete();

        await waitFor(() => {
            expect(button).not.toBeDisabled();
        });
    });
});