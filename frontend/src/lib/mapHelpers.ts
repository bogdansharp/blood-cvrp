export const getBearingDegrees = (from: [number, number], to: [number, number]) => {
	const fromLat = (from[0] * Math.PI) / 180;
	const toLat = (to[0] * Math.PI) / 180;
	const deltaLng = ((to[1] - from[1]) * Math.PI) / 180;

	const y = Math.sin(deltaLng) * Math.cos(toLat);
	const x =
		Math.cos(fromLat) * Math.sin(toLat) - Math.sin(fromLat) * Math.cos(toLat) * Math.cos(deltaLng);

	return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
};
