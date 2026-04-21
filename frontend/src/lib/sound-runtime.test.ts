import { afterEach, describe, expect, it, vi } from 'vitest';

import { createSoundRuntime, type SoundCue, type SoundPlayer } from '$lib/sound-runtime.js';
import { getSoundSettingsStore } from '$lib/sound-settings.js';

function createMockPlayer() {
	const calls: SoundCue[] = [];
	const player: SoundPlayer = {
		play(cue) {
			calls.push(cue);
		}
	};
	return {
		player,
		calls
	};
}

function hostState(overrides: Partial<HostGameState> = {}): HostGameState {
	return {
		id: 'g1',
		join_code: 'ABCD',
		definition_id: 'd1',
		host_enabled: true,
		host_id: 'host',
		connection: 'connected',
		state: 'running',
		phase: 'question_active',
		current_step: 0,
		players: [],
		lastRevision: 1,
		activeStep: {
			id: 'step-1',
			title: 'Question',
			evaluation_type: 'exact_text',
			evaluation_points: 1,
			input_enabled: true,
			input_kind: 'text',
			input_options: [],
			timer: {
				seconds: 10,
				enforced: true,
				started_at: undefined,
				ends_at: undefined,
				remaining_seconds: 10
			}
		},
		displayPhase: 'question_active',
		scoreboardVisible: false,
		buzzerActive: false,
		buzzedPlayerId: undefined,
		disabledBuzzerPlayerIds: [],
		submissionCount: 0,
		pendingReviewCount: 0,
		revealedSubmission: undefined,
		revealedAnswer: undefined,
		endGame: undefined,
		lastReaction: undefined,
		...overrides
	};
}

describe('sound runtime', () => {
	afterEach(() => {
		vi.useRealTimers();
		getSoundSettingsStore('host-display').set({ soundEnabled: true, masterVolume: 0.78 });
		getSoundSettingsStore('controller').set({ soundEnabled: false, masterVolume: 0.35 });
	});

	it('plays buzzer clicks exactly once from the explicit event path', () => {
		const { player, calls } = createMockPlayer();
		const runtime = createSoundRuntime(player, { surface: 'host-display' });

		runtime.syncState(hostState(), { baseline: true });
		runtime.handleEvent({ type_: 'buzzer_clicked', player_id: 'p1' });
		runtime.syncState(
			hostState({
				activeStep: {
					...hostState().activeStep!,
					input_kind: 'buzzer'
				},
				buzzerActive: false,
				buzzedPlayerId: 'p1'
			}),
			{ suppressCues: true }
		);

		expect(calls).toEqual(['buzz']);
	});

	it('does not replay one-shot cues when a snapshot is reapplied', () => {
		const { player, calls } = createMockPlayer();
		const runtime = createSoundRuntime(player, { surface: 'host-display' });
		const state = hostState({
			buzzerActive: true,
			displayPhase: 'answer_reveal',
			endGame: {
				revealed: true,
				sequence_stage: 'podium',
				autoplay_enabled: false,
				final_standings: [],
				podium: [],
				stats_cards: []
			}
		});

		runtime.syncState(state, { baseline: true });
		runtime.syncState(state, { suppressCues: true });

		expect(calls).toEqual([]);
	});

	it('ignores manual score updates for sound playback', () => {
		const { player, calls } = createMockPlayer();
		const runtime = createSoundRuntime(player, { surface: 'host-display' });

		runtime.syncState(hostState(), { baseline: true });
		runtime.handleEvent({ type_: 'update_score', player_id: 'p1', add_score: 5 });

		expect(calls).toEqual([]);
	});

	it('plays answer reveal when the display phase changes', () => {
		const { player, calls } = createMockPlayer();
		const runtime = createSoundRuntime(player, { surface: 'host-display' });

		runtime.syncState(hostState(), { baseline: true });
		runtime.syncState(
			hostState({
				displayPhase: 'answer_reveal'
			})
		);

		expect(calls).toEqual(['answerReveal']);
	});

	it('plays buzzer armed when the buzzer opens, including re-open', () => {
		const { player, calls } = createMockPlayer();
		const runtime = createSoundRuntime(player, { surface: 'host-display' });

		runtime.syncState(
			hostState({
				activeStep: {
					...hostState().activeStep!,
					input_kind: 'buzzer'
				}
			}),
			{ baseline: true }
		);
		runtime.syncState(
			hostState({
				activeStep: {
					...hostState().activeStep!,
					input_kind: 'buzzer'
				},
				buzzerActive: true
			})
		);
		runtime.syncState(
			hostState({
				activeStep: {
					...hostState().activeStep!,
					input_kind: 'buzzer'
				},
				buzzerActive: false
			})
		);
		runtime.syncState(
			hostState({
				activeStep: {
					...hostState().activeStep!,
					input_kind: 'buzzer'
				},
				buzzerActive: true
			})
		);

		expect(calls).toEqual(['buzzerArmed', 'buzzerArmed']);
	});

	it('plays timer warning only once after crossing the threshold', () => {
		vi.useFakeTimers();
		vi.setSystemTime(0);
		const { player, calls } = createMockPlayer();
		const runtime = createSoundRuntime(player, { surface: 'host-display', timerWarningSeconds: 3 });
		const state = hostState({
			activeStep: {
				...hostState().activeStep!,
				timer: {
					seconds: 10,
					enforced: true,
					started_at: 0,
					ends_at: 10,
					remaining_seconds: 10
				}
			}
		});

		runtime.syncState(state, { baseline: true });
		runtime.tick(6_500);
		runtime.tick(7_200);
		runtime.tick(7_900);

		expect(calls).toEqual(['timerWarning']);
	});

	it('plays finale cues for reveal and stage advancement', () => {
		const { player, calls } = createMockPlayer();
		const runtime = createSoundRuntime(player, { surface: 'host-display' });

		runtime.syncState(hostState({ endGame: undefined }), { baseline: true });
		runtime.syncState(
			hostState({
				endGame: {
					revealed: true,
					sequence_stage: 'podium',
					autoplay_enabled: false,
					final_standings: [],
					podium: [],
					stats_cards: []
				}
			})
		);
		runtime.syncState(
			hostState({
				endGame: {
					revealed: true,
					sequence_stage: 'stats',
					autoplay_enabled: false,
					final_standings: [],
					podium: [],
					stats_cards: []
				}
			})
		);
		runtime.syncState(
			hostState({
				endGame: {
					revealed: true,
					sequence_stage: 'scoreboard',
					autoplay_enabled: false,
					final_standings: [],
					podium: [],
					stats_cards: []
				}
			})
		);

		expect(calls).toEqual(['finaleReveal', 'finaleStage', 'winnerPodium']);
	});

	it('plays auto-evaluation success once from answer_judged batch completion', () => {
		const { player, calls } = createMockPlayer();
		const runtime = createSoundRuntime(player, { surface: 'host-display' });

		runtime.syncState(hostState(), { baseline: true });
		runtime.handleEvent(
			{
				type_: 'answer_judged',
				player_id: 'p1',
				accepted: true,
				source: 'auto_evaluation',
				input_kind: 'text',
				batch_id: 'batch-1',
				batch_index: 0,
				batch_size: 2
			},
			hostState()
		);
		runtime.handleEvent(
			{
				type_: 'answer_judged',
				player_id: 'p2',
				accepted: false,
				source: 'auto_evaluation',
				input_kind: 'text',
				batch_id: 'batch-1',
				batch_index: 1,
				batch_size: 2
			},
			hostState()
		);

		expect(calls).toEqual(['correct']);
	});

	it('mutes controller cues by default through policy settings', () => {
		const { player, calls } = createMockPlayer();
		const runtime = createSoundRuntime(player, { surface: 'controller' });

		runtime.syncState(
			hostState({ submissionCount: 0, pendingReviewCount: 2 }) as unknown as ControllerState,
			{ baseline: true }
		);
		runtime.syncState(
			hostState({ submissionCount: 1, pendingReviewCount: 0 }) as unknown as ControllerState
		);

		expect(calls).toEqual([]);
	});

	it('allows controller operational cues when that surface is enabled', () => {
		getSoundSettingsStore('controller').set({ soundEnabled: true, masterVolume: 0.35 });
		const { player, calls } = createMockPlayer();
		const runtime = createSoundRuntime(player, { surface: 'controller' });

		runtime.syncState(
			hostState({ submissionCount: 0, pendingReviewCount: 2 }) as unknown as ControllerState,
			{ baseline: true }
		);
		runtime.syncState(
			hostState({ submissionCount: 1, pendingReviewCount: 0 }) as unknown as ControllerState
		);

		expect(calls).toEqual(['submissionReceived', 'pendingReviewCleared']);
	});
});
