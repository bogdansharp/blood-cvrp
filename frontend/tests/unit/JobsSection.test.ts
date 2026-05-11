// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';

import JobsSection from '../../src/lib/components/JobsSection.svelte';
import type { SolverJobPayload } from '../../src/lib/store';

const makeJob = (overrides: Partial<SolverJobPayload> = {}): SolverJobPayload => ({
    id: 10,
    scenario_id: 42,
    method: 'ortools',
    options: null,
    status: 'finished',
    name: 'Test Job',
    log: [],
    created_at: '2026-01-01T00:00:00Z',
    started_at: '2026-01-01T00:01:00Z',
    finished_at: '2026-01-01T00:02:00Z',
    solution_id: 7,
    solver_ms: 1234,
    preparation_ms: 456,
    results_ms: 78,
    ...overrides
});

describe('JobsSection', () => {
    it('shows the empty state when there are no jobs', () => {
        render(JobsSection);

        expect(screen.getByText('No jobs yet.')).toBeInTheDocument();
    });

    it('renders job status and timing', () => {
        render(JobsSection, {
            props: {
                jobs: [makeJob()]
            }
        });

        expect(screen.getByText('Test Job')).toBeInTheDocument();
        expect(screen.getByText('Finished')).toBeInTheDocument();
        expect(screen.getByText('Method: ortools | Scenario: 42')).toBeInTheDocument();
        expect(screen.getByText('Timing: prep 456ms, solve 1234ms, results 78ms')).toBeInTheDocument();
    });

    it('renders solution id when present', () => {
        render(JobsSection, {
            props: {
                jobs: [makeJob({ solution_id: 99 })]
            }
        });

        expect(screen.getByText('Solution: 99')).toBeInTheDocument();
    });

    it('renders logs when present', () => {
        render(JobsSection, {
            props: {
                jobs: [
                    makeJob({
                        log: [
                            {
                                timestamp: '2026-01-01T00:01:00Z',
                                level: 'info',
                                message: 'Started preparation'
                            },
                            {
                                timestamp: '2026-01-01T00:02:00Z',
                                level: 'error',
                                message: 'Solver failed'
                            }
                        ]
                    })
                ]
            }
        });

        expect(screen.getByText('Log (2)')).toBeInTheDocument();
        expect(screen.getByText('Started preparation')).toBeInTheDocument();
        expect(screen.getByText('Solver failed')).toBeInTheDocument();
        expect(screen.getByText('info')).toBeInTheDocument();
        expect(screen.getByText('error')).toBeInTheDocument();
    });
});