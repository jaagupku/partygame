import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { render, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import DrawingPlayer from './DrawingPlayer.svelte';
import DrawingGallery from './DrawingGallery.svelte';
import DrawingInput from '$lib/components/DrawingInput.svelte';
import { drawingText } from './helpers';
import { locale } from '$lib/i18n';

const view = (): DrawingGameView => ({
	phase: 'writing',
	phase_id: 1,
	deadline: Date.now() / 1000 + 90,
	remaining_seconds: null,
	paused: false,
	language: 'en',
	participant_ids: ['p1', 'p2', 'p3'],
	ready_ids: [],
	is_participant: true,
	prompt: { topic: '', criterion: '', revision: 0 },
	assignments: [],
	matchup_number: 0,
	matchup_count: 0,
	gallery: []
});
function player(current = view()) {
	const send = vi.fn();
	const component = render(DrawingPlayer, {
		view: current,
		runId: 'run',
		playerId: 'p1',
		organizer: false,
		connected: true,
		send
	});
	return { send, component };
}
async function pump() {
	await vi.advanceTimersByTimeAsync(410);
	await tick();
}
beforeEach(() => {
	vi.useFakeTimers();
	localStorage.clear();
	locale.set('en');
});
afterEach(() => {
	cleanup();
	vi.useRealTimers();
	vi.unstubAllGlobals();
});

describe('drawing draft recovery', () => {
	it('restores an unsent writing draft after a remount', async () => {
		const first = player();
		await fireEvent.input(first.component.getByLabelText('Drawing topic'), {
			target: { value: 'A strange journey' }
		});
		first.component.unmount();
		const second = player();
		expect((second.component.getByLabelText('Drawing topic') as HTMLTextAreaElement).value).toBe(
			'A strange journey'
		);
		await pump();
		expect(second.send).toHaveBeenCalledWith(
			expect.objectContaining({ action: 'prompt', topic: 'A strange journey', revision: 0 })
		);
	});
	it('saves edits made during an in-flight save using the acknowledged revision', async () => {
		const { component, send } = player();
		await fireEvent.input(component.getByLabelText('Drawing topic'), {
			target: { value: 'First' }
		});
		await pump();
		const first = send.mock.calls[0][0];
		await fireEvent.input(component.getByLabelText('Drawing topic'), {
			target: { value: 'Second' }
		});
		await pump();
		expect(send).toHaveBeenCalledTimes(1);
		await component.rerender({
			ack: {
				type_: 'drawing_ack',
				request_id: first.request_id,
				run_id: 'run',
				status: 'ok',
				revision: 1
			}
		});
		await pump();
		expect(send).toHaveBeenLastCalledWith(
			expect.objectContaining({ topic: 'Second', revision: 1 })
		);
	});
	it('keeps a newer local edit when refresh follows a save whose acknowledgement was lost', async () => {
		const first = player();
		await fireEvent.input(first.component.getByLabelText('Drawing topic'), {
			target: { value: 'First' }
		});
		await pump();
		await fireEvent.input(first.component.getByLabelText('Drawing topic'), {
			target: { value: 'Second' }
		});
		first.component.unmount();
		const next = view();
		next.prompt = { topic: 'First', criterion: '', revision: 1 };
		const second = player(next);
		expect((second.component.getByLabelText('Drawing topic') as HTMLTextAreaElement).value).toBe(
			'Second'
		);
		await pump();
		expect(second.send).toHaveBeenCalledWith(
			expect.objectContaining({ topic: 'Second', revision: 1 })
		);
	});
	it('retains an in-flight local draft when the organizer pauses and retries after resume', async () => {
		const { component, send } = player();
		await fireEvent.input(component.getByLabelText('Drawing topic'), {
			target: { value: 'Journey' }
		});
		await pump();
		const first = send.mock.calls[0][0];
		const paused = { ...view(), paused: true, deadline: null, remaining_seconds: 70 };
		await component.rerender({
			view: paused,
			ack: {
				type_: 'drawing_ack',
				request_id: first.request_id,
				run_id: 'run',
				status: 'error',
				reason: 'closed',
				view: paused
			}
		});
		await pump();
		expect(send).toHaveBeenCalledTimes(1);
		expect((component.getByLabelText('Drawing topic') as HTMLTextAreaElement).value).toBe(
			'Journey'
		);
		await component.rerender({ view: view() });
		await pump();
		expect(send).toHaveBeenLastCalledWith(
			expect.objectContaining({ action: 'prompt', topic: 'Journey', revision: 0 })
		);
	});
	it('waits for the draft acknowledgement before marking the player ready', async () => {
		const { component, send } = player();
		await fireEvent.input(component.getByLabelText('Drawing topic'), {
			target: { value: 'Journey' }
		});
		await fireEvent.input(component.getByLabelText('Voting criterion'), {
			target: { value: 'Most chaotic' }
		});
		await fireEvent.click(component.getByRole('button', { name: 'Done' }));
		expect(send).toHaveBeenCalledTimes(1);
		const first = send.mock.calls[0][0];
		expect(first.action).toBe('prompt');
		await component.rerender({
			ack: {
				type_: 'drawing_ack',
				request_id: first.request_id,
				run_id: 'run',
				status: 'ok',
				revision: 1
			}
		});
		await pump();
		expect(send).toHaveBeenLastCalledWith(expect.objectContaining({ action: 'ready' }));
	});
});

it('resolves built-in text using the game language independently of UI language', () => {
	locale.set('et');
	expect(drawingText({ text: '', fallback: 0 }, 'topic', 'en')).toBe('A celebration');
	expect(drawingText({ text: '', fallback: 0 }, 'criterion', 'et')).toBe('Kõige kaootilisem');
});

it('rotates the gallery at seven seconds and supports pause and manual navigation', async () => {
	vi.stubGlobal(
		'fetch',
		vi.fn().mockResolvedValue({
			ok: true,
			json: async () => ({ w: 512, h: 384, s: [[0, 8, 0, [5, 5, 20, 20]]] })
		})
	);
	const items: MashupArtwork[] = [0, 1, 2].map((i) => ({
		id: String(i),
		topic: { text: `Topic ${i}`, fallback: null },
		value: null,
		revision: 0,
		vote_count: 1,
		points: 500,
		own: false
	}));
	const { getByRole } = render(DrawingGallery, {
		items,
		lobbyId: 'g',
		runId: 'run',
		language: 'en'
	});
	await vi.advanceTimersByTimeAsync(6000);
	expect(getByRole('heading', { name: 'Drawing gallery · 1/3' })).toBeTruthy();
	await vi.advanceTimersByTimeAsync(1000);
	expect(getByRole('heading', { name: 'Drawing gallery · 2/3' })).toBeTruthy();
	await fireEvent.click(getByRole('button', { name: 'Pause' }));
	await vi.advanceTimersByTimeAsync(8000);
	expect(getByRole('heading', { name: 'Drawing gallery · 2/3' })).toBeTruthy();
	await fireEvent.click(getByRole('button', { name: 'Next' }));
	expect(getByRole('heading', { name: 'Drawing gallery · 3/3' })).toBeTruthy();
});

it('does not save again when the pointer leaves an idle canvas', async () => {
	const onChange = vi.fn();
	const { container } = render(DrawingInput, {
		disabled: false,
		onSubmit: vi.fn(),
		onChange,
		initialDrawing: { w: 512, h: 384, s: [[0, 8, 0, [5, 5, 20, 20]]] }
	});
	const canvas = container.querySelector('canvas.drawing-input-canvas')!;
	await fireEvent.pointerLeave(canvas);
	await fireEvent.pointerUp(canvas);
	expect(onChange).not.toHaveBeenCalled();
});

it('blocks the entire ballot for artists and restores voting on the next matchup', async () => {
	const current: DrawingGameView = {
		...view(),
		phase: 'voting',
		matchup: {
			id: 'match',
			topic: { text: 'Topic', fallback: null },
			criterion: { text: 'Criterion', fallback: null },
			drawings: [true, false].map((own, i) => ({
				id: String(i),
				topic: { text: 'Topic', fallback: null },
				own,
				value: null,
				revision: 0,
				vote_count: 0,
				points: 0
			})),
			can_commend_topic: true,
			can_commend_criterion: true,
			topic_points: 0,
			criterion_points: 0
		}
	};
	const { component, send } = player(current);
	expect(component.getByText("You can't vote right now")).toBeTruthy();
	expect(component.queryAllByRole('button')).toHaveLength(0);
	expect(component.queryAllByRole('checkbox')).toHaveLength(0);
	await pump();
	expect(send).not.toHaveBeenCalled();
	await component.rerender({
		view: {
			...current,
			phase_id: 2,
			matchup: {
				...current.matchup!,
				id: 'next',
				drawings: current.matchup!.drawings.map((art) => ({ ...art, own: false }))
			}
		}
	});
	expect(component.queryByText("You can't vote right now")).toBeNull();
	await fireEvent.click(component.getByRole('button', { name: /^A$/ }));
	await pump();
	expect(send).toHaveBeenCalledWith(
		expect.objectContaining({
			action: 'ballot',
			matchup_id: 'next',
			ballot: expect.objectContaining({ drawing_id: '0' })
		})
	);
});
