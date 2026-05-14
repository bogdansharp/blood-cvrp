<svelte:options runes={false} />

<script lang="ts">
    import type { LayerGroup, Map as LeafletMap } from 'leaflet';
    import { onDestroy, onMount } from 'svelte';
    import 'leaflet/dist/leaflet.css';

    import { getBearingDegrees } from '$lib/mapHelpers';
    import {
        locationKey,
        makeHospitalFromLocation
    } from '$lib/scenarioEditorHelpers';
    import type { AppViewState, Hospital, ScenarioPayload } from '$lib/store';

    export let state: AppViewState;
    export let editorMode = false;
    export let editorDraft: ScenarioPayload | null = null;
    export let addDepotMode = false;
    export let editorVersion = 0;

    export let addEditorLocation: (location: Hospital) => void;
    export let removeEditorLocation: (location: Hospital) => void;
    export let makeHospitalFromMapPoint: (lat: number, lng: number) => Promise<Hospital | null>;

    const defaultCenter: [number, number] = [53.331, -8.092];
    const defaultZoom = 8;

    let mapContainer: HTMLDivElement | null = null;
    let map: LeafletMap | null = null;
    let mapLayers: LayerGroup | null = null;
    let leaflet: typeof import('leaflet') | null = null;
    let lastMapKey = '';
    let lastFitBoundsKey = '';
    let nextPendingSnapId = 1;
    let pendingSnapPoints: { id: number; point: [number, number] }[] = [];

    type MarkerKind = 'hospital' | 'customer' | 'depot';
    type MarkerAction = 'add' | 'delete' | 'none';

    const markerColors: Record<MarkerKind, string> = {
        hospital: '#555',
        customer: '#b23b00',
        depot: '#0f4c81'
    };

    const deleteCursor =
        `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3Cline x1='6' y1='6' x2='18' y2='18' stroke='%23dc2626' stroke-width='3' stroke-linecap='round'/%3E%3Cline x1='18' y1='6' x2='6' y2='18' stroke='%23dc2626' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E") 12 12, pointer`;

    const isInsideIreland = (lat: number, lng: number): boolean => {
        return lat >= 51.3 && lat <= 55.6 && lng >= -10.8 && lng <= -5.4;
    };

    const drawMarker = (
        hospital: Hospital,
        kind: MarkerKind,
        label: string,
        action: MarkerAction = 'none',
        onClick?: () => void
    ) => {
        if (!leaflet || !mapLayers || !map) {
            return;
        }

        const color = markerColors[kind];
        const radius = kind === 'depot' ? 7 : 5;

        const marker = leaflet
            .circleMarker([hospital.lat, hospital.lng], {
                radius,
                color,
                fillColor: color,
                fillOpacity: 0.85,
                interactive: true,
                bubblingMouseEvents: false
            })
            .bindPopup(`<strong>${label}:</strong> ${hospital.name || 'Custom location'}`)
            .addTo(mapLayers);

        const element = marker.getElement() as HTMLElement | null;

        if (element && action !== 'none') {
            element.style.cursor = action === 'delete' ? deleteCursor : 'pointer';
        }

        if (!onClick || action === 'none') {
            return;
        }

        const hoverColor =
            action === 'delete'
                ? '#991b1b'
                : addDepotMode
                  ? markerColors.depot
                  : markerColors.customer;

        marker.on('click', onClick);

        marker.on('mouseover', () => {
            marker.setStyle({
                color: hoverColor,
                fillColor: hoverColor,
                radius: radius + 2,
                fillOpacity: 0.95
            });

            map?.getContainer().style.setProperty(
                'cursor',
                action === 'delete' ? deleteCursor : 'pointer'
            );
        });

        marker.on('mouseout', () => {
            marker.setStyle({
                color,
                fillColor: color,
                radius,
                fillOpacity: 0.85
            });

            map?.getContainer().style.setProperty('cursor', editorMode ? 'pointer' : '');
        });
    };

    const handleEditorMapClick = async (event: { latlng: { lat: number; lng: number } }) => {
        if (!editorMode || !editorDraft) {
            return;
        }

        if (!isInsideIreland(event.latlng.lat, event.latlng.lng)) {
            console.warn('Clicked point is outside Ireland');
            return;
        }

        const pendingId = nextPendingSnapId++;
        const point: [number, number] = [event.latlng.lat, event.latlng.lng];

        pendingSnapPoints = [...pendingSnapPoints, { id: pendingId, point }];
        updateMapLayers(false);

        const hospital = await makeHospitalFromMapPoint(event.latlng.lat, event.latlng.lng);

        pendingSnapPoints = pendingSnapPoints.filter((item) => item.id !== pendingId);
        updateMapLayers(false);

        if (!hospital) {
            return;
        }

        addEditorLocation(hospital);
    };

    const addDirectionArrows = (
        points: [number, number][],
        color: string,
        layers: LayerGroup
    ) => {
        if (!leaflet || points.length < 2) {
            return;
        }

        const arrowCount = Math.min(4, Math.max(1, Math.floor(points.length / 12)));
        const step = Math.max(2, Math.floor(points.length / (arrowCount + 1)));

        for (let index = step; index < points.length; index += step) {
            const previous = points[index - 1];
            const current = points[index];
            const angle = getBearingDegrees(previous, current);

            const icon = leaflet.divIcon({
                className: 'route-arrow-icon',
                html: `
                    <svg
                        width="20" height="20" viewBox="0 0 20 20"
                        style="transform: rotate(${angle}deg);color: ${color};display: block;"
                        aria-hidden="true"
                    >
                        <path d="M10 2 L16 14 L10 11 L4 14 Z" fill="currentColor"/>
                    </svg>
                `,
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            });

            leaflet
                .marker(current, {
                    icon,
                    interactive: false,
                    keyboard: false
                })
                .addTo(layers);
        }
    };

    const ensureMap = async () => {
        if (map || !mapContainer) {
            return;
        }

        const loaded = await import('leaflet');
        leaflet = loaded;
        map = loaded.map(mapContainer).setView(defaultCenter, defaultZoom);

        loaded
            .tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '&copy; OpenStreetMap contributors'
            })
            .addTo(map);

        mapLayers = loaded.layerGroup().addTo(map);
        updateMapLayers();
        map.on('click', handleEditorMapClick);
    };

    const updateMapLayers = (shouldFitBounds = false) => {
        if (!map || !mapLayers || !leaflet) {
            return;
        }

        const layers = mapLayers;
        const l = leaflet;
        const bounds: Array<[number, number]> = [];

        layers.clearLayers();

        const scenario = state.scenario;
        const hospitals = state.hospitals;

        map.getContainer().style.cursor = '';

        if (editorMode && editorDraft) {
            map.getContainer().style.cursor = 'pointer';

            const selectedCustomerKeys = new Set(editorDraft.customers.map(locationKey));
            const depotKeys = new Set(editorDraft.depots.map(locationKey));
            const predefinedKeys = new Set<string>();

            for (const location of hospitals) {
                const hospital = makeHospitalFromLocation(location);
                const key = locationKey(hospital);

                predefinedKeys.add(key);
                bounds.push([hospital.lat, hospital.lng]);

                if (depotKeys.has(key)) {
                    drawMarker(hospital, 'depot', 'Depot', 'delete', () =>
                        removeEditorLocation(hospital)
                    );
                } else if (selectedCustomerKeys.has(key)) {
                    drawMarker(hospital, 'customer', 'Customer', 'delete', () =>
                        removeEditorLocation(hospital)
                    );
                } else {
                    drawMarker(hospital, 'hospital', 'Available', 'add', () =>
                        addEditorLocation(hospital)
                    );
                }
            }

            for (const customer of editorDraft.customers) {
                if (!predefinedKeys.has(locationKey(customer))) {
                    bounds.push([customer.lat, customer.lng]);
                    drawMarker(customer, 'customer', 'Customer', 'delete', () =>
                        removeEditorLocation(customer)
                    );
                }
            }

            for (const { point } of pendingSnapPoints) {
                leaflet
                    .circleMarker(point, {
                        radius: 6,
                        color: markerColors.customer,
                        fillColor: markerColors.customer,
                        fillOpacity: 0,
                        weight: 2,
                        interactive: false
                    })
                    .addTo(layers);

                bounds.push(point);
            }

            for (const depot of editorDraft.depots) {
                if (!predefinedKeys.has(locationKey(depot))) {
                    bounds.push([depot.lat, depot.lng]);
                    drawMarker(depot, 'depot', 'Depot', 'delete', () =>
                        removeEditorLocation(depot)
                    );
                }
            }

            if (shouldFitBounds && bounds.length > 0) {
                map.fitBounds(bounds, { padding: [24, 24] });
            }

            return;
        }

        if (!scenario && hospitals.length === 0) {
            if (shouldFitBounds) {
                map.setView(defaultCenter, defaultZoom);
            }
            return;
        }

        if (!scenario) {
            hospitals.forEach((location) => {
                const hospital = makeHospitalFromLocation(location);
                bounds.push([hospital.lat, hospital.lng]);
                drawMarker(hospital, 'hospital', 'Hospital');
            });

            if (bounds.length > 0 && shouldFitBounds) {
                map.fitBounds(bounds, { padding: [24, 24] });
            }

            return;
        }

        scenario.customers.forEach((customer) => {
            const position: [number, number] = [customer.lat, customer.lng];
            bounds.push(position);
            drawMarker(customer, 'customer', 'Customer');
        });

        if (state.solution) {
            state.solution.routes.forEach((route, routeIndex) => {
                const routePoints: [number, number][] = [];

                const routeColors = [
                    '#0f4c81',
                    '#b23b00',
                    '#1f7a3f',
                    '#7c3aed',
                    '#c2410c',
                    '#be123c',
                    '#0f766e',
                    '#a16207'
                ];

                let previous: (typeof route.sequence)[number] | null = null;

                route.sequence.forEach((current) => {
                    if (
                        !Number.isFinite(current.lat) ||
                        !Number.isFinite(current.lng) ||
                        !Number.isFinite(current.lat_e6) ||
                        !Number.isFinite(current.lng_e6)
                    ) {
                        console.warn('Route hospital has invalid coordinates', current);
                        return;
                    }

                    bounds.push([current.lat, current.lng]);

                    if (previous) {
                        const key = `${previous.lat_e6}_${previous.lng_e6}_${current.lat_e6}_${current.lng_e6}`;
                        const geometry = state.geometries.get(key);

                        if (geometry && geometry.length >= 2) {
                            routePoints.push(...geometry);
                        } else {
                            routePoints.push(
                                [previous.lat, previous.lng],
                                [current.lat, current.lng]
                            );
                        }
                    }

                    previous = current;
                });

                if (routePoints.length >= 2) {
                    const distanceKm = (route.total_distance / 1000).toFixed(3);
                    const totalMinutes = Math.round(route.total_travel_time / 60);
                    const hours = Math.floor(totalMinutes / 60);
                    const minutes = totalMinutes % 60;
                    const formattedTime = `${hours}h ${String(minutes).padStart(2, '0')}m`;
                    const routeColor = routeColors[routeIndex % routeColors.length];

                    const routeLine = l
                        .polyline(routePoints, { color: routeColor, weight: 3, opacity: 0.8 })
                        .bindPopup(
                            `Route ${routeIndex + 1}<br />` +
                                `Distance: ${distanceKm} km<br />` +
                                `Time: ${formattedTime} <br />` +
                                `Capacity: ${route.vehicle_capacity_used} / ${route.vehicle_capacity}`
                        )
                        .addTo(layers);

                    routeLine.on('click', () => {
                        routeLine.bringToFront();
                    });

                    addDirectionArrows(routePoints, routeColor, layers);
                }
            });
        }

        scenario.depots.forEach((depot) => {
            const position: [number, number] = [depot.lat, depot.lng];
            bounds.push(position);
            drawMarker(depot, 'depot', 'Depot');
        });

        if (shouldFitBounds) {
            if (bounds.length > 0) {
                map.fitBounds(bounds, { padding: [24, 24] });
            } else {
                map.setView(defaultCenter, defaultZoom);
            }
        }
    };

    const getMapKey = (value: AppViewState) => {
        const scnId = value.scenario?.id ?? 'none';
        const solId = value.solution?.id ?? 'none';
        const hospCount = value.hospitals.length;
        const routesCount = value.solution?.routes.length ?? 0;
        const geomVer = value.geometryVersion;
        const editorState = `${editorMode}|${editorVersion}|${addDepotMode}|${pendingSnapPoints.length}`;
        return `${scnId}|${solId}|${hospCount}|${routesCount}|${geomVer}|${editorState}`;
    };

    const getFitBoundsKey = (value: AppViewState) => {
        const scnId = value.scenario?.id ?? 'none';
        const hospCount = value.hospitals.length;
        const depotsCount = value.scenario?.depots.length ?? 0;
        const cstmCount = value.scenario?.customers.length ?? 0;

        return `${scnId}|${hospCount}|${depotsCount}|${cstmCount}`;
    };

    onMount(() => {
        void ensureMap();

        return () => {
            if (map) {
                map.remove();
                map = null;
                mapLayers = null;
                leaflet = null;
            }
        };
    });

    onDestroy(() => {
        if (map) {
            map.remove();
            map = null;
            mapLayers = null;
            leaflet = null;
        }
    });

    $: if (map && mapLayers && leaflet) {
        const editorCustomerCount = editorDraft?.customers.length ?? 0;
        const editorDepotCount = editorDraft?.depots.length ?? 0;

        const nextMapKey = [
            getMapKey(state),
            editorMode,
            editorVersion,
            addDepotMode,
            editorCustomerCount,
            editorDepotCount
        ].join('|');

        const nextFitBoundsKey = [
            getFitBoundsKey(state),
            editorMode,
            editorDraft?.id ?? 'none'
        ].join('|');

        if (nextMapKey !== lastMapKey) {
            const shouldFitBounds = nextFitBoundsKey !== lastFitBoundsKey;

            lastMapKey = nextMapKey;
            lastFitBoundsKey = nextFitBoundsKey;

            updateMapLayers(shouldFitBounds);
        }
    }
</script>

<div
    bind:this={mapContainer}
    class="relative h-[54dvh] min-h-70 w-full border-b border-neutral-300 min-[821px]:absolute min-[821px]:inset-0 min-[821px]:h-full min-[821px]:border-b-0"
></div>