import { expect, test, type Page, type Route } from '@playwright/test';

const apiBase = '**/api/v1';

const scenarioReduced = {
	id: 42,
	name: 'Scenario Alpha',
	vehicles_count: 1,
	depots_count: 1,
	customers_count: 1,
	description: 'Test scenario'
};

const depot = {
	id: 100,
	name: 'Main Depot',
	lat_e6: 53100000,
	lng_e6: -8200000,
	display_lat_e6: 53100000,
	display_lng_e6: -8200000,
	snap_distance_m: 0,
	category: 'Hospital',
	subcategory: 'Depot',
	address: 'Depot Road',
	eircode: 'D01DEPOT',
	demand: 0,
	lat: 53.1,
	lng: -8.2,
	display_lat: 53.1,
	display_lng: -8.2
};

const customer = {
	id: 200,
	name: 'Customer A',
	lat_e6: 53200000,
	lng_e6: -8300000,
	display_lat_e6: 53200000,
	display_lng_e6: -8300000,
	snap_distance_m: 0,
	category: 'Hospital',
	subcategory: 'General',
	address: 'Customer Street',
	eircode: 'C01A',
	demand: 4,
	lat: 53.2,
	lng: -8.3,
	display_lat: 53.2,
	display_lng: -8.3
};

const scenario = {
	id: 42,
	name: 'Scenario Alpha',
	description: 'Test scenario',
	vehicles: [{ capacity: 10, quantity: 2 }],
	depots: [depot],
	customers: [customer]
};

const hospitals = [
	{
		id: 1,
		name: 'Hospital List Item',
		lat: 53,
		lng: -8,
		display_lat: 53,
		display_lng: -8,
		category: 'Hospital',
		subcategory: 'General',
		address: 'Hospital Road',
		eircode: 'H01',
		demand: 1
	}
];

const queuedJob = {
	id: 10,
	scenario_id: 42,
	method: 'clarke_wright_savings',
	options: null,
	status: 'queued',
	name: 'Test Job',
	log: [],
	created_at: '2026-01-01T00:00:00Z',
	started_at: null,
	finished_at: null,
	solution_id: null,
	solver_ms: 0,
	preparation_ms: 0,
	results_ms: 0
};

const finishedJob = {
	...queuedJob,
	status: 'finished',
	solution_id: 7,
	started_at: '2026-01-01T00:01:00Z',
	finished_at: '2026-01-01T00:02:00Z',
	solver_ms: 123,
	preparation_ms: 45,
	results_ms: 6,
	log: [
		{
			timestamp: '2026-01-01T00:02:00Z',
			level: 'info',
			message: 'Successfully solved scenario'
		}
	]
};

const solution = {
	id: 7,
	name: 'Solution 7',
	scenario_id: 42,
	method: 'clarke_wright_savings',
	total_distance: 1000,
	total_travel_time: 600,
	options: null,
	created_at: '2026-01-01T00:02:00Z',
	routes: [
		{
			src: depot,
			dst: depot,
			sequence: [depot, customer, depot],
			total_distance: 1000,
			total_travel_time: 600,
			vehicle_capacity: 10,
			vehicle_capacity_used: 4
		}
	]
};

const fulfillJson = async (route: Route, body: unknown, status = 200) => {
	await route.fulfill({
		status,
		headers: {
			'access-control-allow-origin': '*',
			'content-type': 'application/json'
		},
		body: JSON.stringify(body)
	});
};

const mockBaseBackend = async (page: Page, unexpectedApiRequests: string[] = []) => {
	await page.route(`${apiBase}/**`, async (route) => {
		const request = route.request();

		unexpectedApiRequests.push(`${request.method()} ${request.url()}`);

		await fulfillJson(
			route,
			{
				detail: `Unexpected API request: ${request.method()} ${request.url()}`
			},
			500
		);
	});

	await page.route(`${apiBase}/scenarios/`, async (route) => {
		await fulfillJson(route, [scenarioReduced]);
	});

	await page.route(`${apiBase}/hospitals/`, async (route) => {
		await fulfillJson(route, hospitals);
	});

	await page.route(`${apiBase}/scenarios/42`, async (route) => {
		await fulfillJson(route, scenario);
	});

	await page.route(
		(url) => url.href === `${apiBase}/jobs` || url.href.startsWith(`${apiBase}/jobs?`),
		async (route) => {
			await fulfillJson(route, []);
		}
	);

	await page.route(
		(url) =>
			url.href === `${apiBase}/solutions` ||
			url.href === `${apiBase}/solutions/` ||
			url.href.startsWith(`${apiBase}/solutions?`) ||
			url.href.startsWith(`${apiBase}/solutions/?`),
		async (route) => {
			await fulfillJson(route, []);
		}
	);
};

test('home page loads', async ({ page }) => {
	await page.goto('http://localhost:5173/');

	await expect(page.getByRole('heading', { name: 'Blood CVRP App' })).toBeVisible();
});

test('user selects scenario and solve button becomes enabled', async ({ page }) => {
	await mockBaseBackend(page);

	await page.goto('/');

	await expect(page.getByRole('heading', { name: 'Blood CVRP App' })).toBeVisible();

	const solveButton = page.getByRole('button', { name: 'Solve' });
	await expect(solveButton).toBeDisabled();

	await page.getByLabel('Scenario').selectOption('42');

	await expect(page.getByRole('heading', { name: 'Scenario Alpha' })).toBeVisible();
	await expect(page.getByText('Main Depot')).toBeVisible();
	await expect(page.getByText('Customers (1)')).toBeVisible();
	await page.getByText('Customers (1)').click();
	await expect(page.getByText('Customer A')).toBeVisible();
	await expect(solveButton).toBeEnabled();
});

test('user solves scenario and app stays usable after loading route geometry', async ({ page }) => {
	await mockBaseBackend(page);

	const pageErrors: Error[] = [];
	page.on('pageerror', (error) => {
		pageErrors.push(error);
	});

	let pollCount = 0;
	let solutionRequested = false;
	let geometryRequested = false;

	await page.route(`${apiBase}/jobs/run/42**`, async (route) => {
		await fulfillJson(route, queuedJob);
	});

	await page.route(`${apiBase}/jobs/10`, async (route) => {
		pollCount += 1;
		await fulfillJson(route, pollCount === 1 ? { ...queuedJob, status: 'running' } : finishedJob);
	});

	await page.route(`${apiBase}/solutions/7`, async (route) => {
		solutionRequested = true;
		await fulfillJson(route, solution);
	});

	await page.route(`${apiBase}/routing/geometry**`, async (route) => {
		geometryRequested = true;
		await fulfillJson(route, [
			[53.1, -8.2],
			[53.15, -8.25],
			[53.2, -8.3]
		]);
	});

	await page.goto('/');

	await page.getByLabel('Scenario').selectOption('42');
	await page.getByRole('button', { name: 'Solve' }).click();

	await expect.poll(() => pollCount).toBeGreaterThanOrEqual(2);
	await expect.poll(() => solutionRequested).toBe(true);
	await expect.poll(() => geometryRequested).toBe(true);

	await expect(page.getByRole('heading', { name: 'Scenario Alpha' })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Solve' })).toBeEnabled();

	expect(pageErrors).toEqual([]);
});
