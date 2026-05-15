// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import JobsSection from '../../src/lib/components/JobsSection.svelte';
import type { SolverJobPayload } from '../../src/lib/store';

const mocks = vi.hoisted(() => ({
	cancelJob: vi.fn()
}));

vi.mock('$lib/store', async (importOriginal) => {
	const actual = await importOriginal<typeof import('$lib/store')>();

	return {
		...actual,
		cancelJob: mocks.cancelJob
	};
});

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
	beforeEach(() => {
		mocks.cancelJob.mockReset();
	});
	afterEach(() => {
		cleanup();
		vi.restoreAllMocks();
	});

	it('shows the empty state when there are no jobs', () => {
		render(JobsSection);

		expect(screen.getByText('No jobs yet.')).toBeInTheDocument();
	});

	it('renders job summary', () => {
		const { container } = render(JobsSection, {
			props: {
				jobs: [makeJob()]
			}
		});
		const text = container.textContent ?? '';

		expect(screen.getByText('Job #10')).toBeInTheDocument();
		expect(screen.getByText('Finished', { selector: 'span' })).toBeInTheDocument();

		expect(text).toContain('Scenario: 42');
		expect(text).toContain('prep 456ms');
		expect(text).toContain('solve 1234ms');
		expect(text).toContain('results 78ms');
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

	it('shows cancel button for queued and running jobs only', () => {
		render(JobsSection, {
			props: {
				jobs: [
					makeJob({
						id: 1,
						name: 'Queued Job',
						status: 'queued',
						finished_at: null,
						solution_id: null
					}),
					makeJob({
						id: 2,
						name: 'Running Job',
						status: 'running',
						finished_at: null,
						solution_id: null
					}),
					makeJob({
						id: 3,
						name: 'Finished Job',
						status: 'finished'
					})
				]
			}
		});
		const buttons = screen.getAllByRole('button', { name: 'Cancel' });

		expect(buttons).toHaveLength(2);
	});

	it('calls cancelJob when cancel button is clicked', async () => {
		mocks.cancelJob.mockResolvedValueOnce(undefined);

		render(JobsSection, {
			props: {
				jobs: [
					makeJob({
						id: 123,
						status: 'running',
						finished_at: null,
						solution_id: null
					})
				]
			}
		});
		await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

		await waitFor(() => {
			expect(mocks.cancelJob).toHaveBeenCalledWith(123);
		});
	});

	it('disables cancel button after cancel is requested', async () => {
		mocks.cancelJob.mockResolvedValueOnce(undefined);

		render(JobsSection, {
			props: {
				jobs: [
					makeJob({
						id: 123,
						status: 'running',
						finished_at: null,
						solution_id: null
					})
				]
			}
		});
		const button = screen.getByRole('button', { name: 'Cancel' });
		await fireEvent.click(button);
		await waitFor(() => {
			expect(button).toBeDisabled();
		});
		await fireEvent.click(button);

		expect(mocks.cancelJob).toHaveBeenCalledTimes(1);
	});
});
