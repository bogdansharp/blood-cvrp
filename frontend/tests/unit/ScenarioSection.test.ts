// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';

import ScenarioSection from '../../src/lib/components/ScenarioSection.svelte';

describe('ScenarioSection', () => {
    it('shows the empty state when no scenario is provided', () => {
        render(ScenarioSection);

        expect(screen.getByText('No scenario selected.')).toBeInTheDocument();
    });

    it('shows the loading state when loading is true', () => {
        render(ScenarioSection, { props: { loading: true } });

        expect(screen.getByText('Loading scenario...')).toBeInTheDocument();
    });
});
