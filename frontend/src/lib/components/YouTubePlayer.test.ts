import { render } from '@testing-library/svelte';
import { tick } from 'svelte';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import YouTubePlayer from '$lib/components/YouTubePlayer.svelte';
import { loadYouTubeIframeApi } from '$lib/media/youtube.js';

vi.mock('$lib/media/youtube.js', async () => {
	const actual =
		await vi.importActual<typeof import('$lib/media/youtube.js')>('$lib/media/youtube.js');
	return {
		...actual,
		loadYouTubeIframeApi: vi.fn()
	};
});

type MockYouTubePlayer = {
	destroy: ReturnType<typeof vi.fn>;
	getPlayerState: ReturnType<typeof vi.fn>;
	pauseVideo: ReturnType<typeof vi.fn>;
	playVideo: ReturnType<typeof vi.fn>;
	seekTo: ReturnType<typeof vi.fn>;
};

const TEST_MEDIA = {
	videoId: 'dQw4w9WgXcQ',
	embedUrl: 'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ',
	startSeconds: 0
};

async function flushEffects() {
	await Promise.resolve();
	await tick();
	await Promise.resolve();
}

describe('YouTubePlayer', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		delete window.YT;
	});

	it('pauses and resumes the existing player across rerenders', async () => {
		const mockPlayer: MockYouTubePlayer = {
			destroy: vi.fn(),
			getPlayerState: vi.fn(() => 1),
			pauseVideo: vi.fn(),
			playVideo: vi.fn(),
			seekTo: vi.fn()
		};

		const mockNamespace = {
			PlayerState: {
				BUFFERING: 3,
				PLAYING: 1
			},
			Player: vi.fn(
				(
					_element: HTMLDivElement,
					options: {
						events?: {
							onReady?: () => void;
							onStateChange?: (event: { data: number }) => void;
						};
					}
				) => {
					queueMicrotask(() => {
						options.events?.onReady?.();
					});
					return mockPlayer;
				}
			)
		};

		window.YT = mockNamespace as unknown as YouTubeNamespace;
		vi.mocked(loadYouTubeIframeApi).mockResolvedValue(mockNamespace as unknown as YouTubeNamespace);

		const view = render(YouTubePlayer, {
			media: TEST_MEDIA,
			shouldPauseMedia: false,
			shouldResumePausedMedia: false
		});

		await flushEffects();

		expect(mockNamespace.Player).toHaveBeenCalled();
		expect(mockPlayer.playVideo).toHaveBeenCalled();
		expect(mockPlayer.pauseVideo).not.toHaveBeenCalled();
		expect(mockPlayer.destroy).not.toHaveBeenCalled();

		await view.rerender({
			media: { ...TEST_MEDIA },
			shouldPauseMedia: true,
			shouldResumePausedMedia: false
		});
		await flushEffects();

		expect(mockPlayer.pauseVideo).toHaveBeenCalled();
		expect(mockPlayer.destroy).not.toHaveBeenCalled();
		expect(mockNamespace.Player).toHaveBeenCalledTimes(1);

		await view.rerender({
			media: { ...TEST_MEDIA },
			shouldPauseMedia: false,
			shouldResumePausedMedia: true
		});
		await flushEffects();

		expect(mockPlayer.playVideo).toHaveBeenCalled();
		expect(mockPlayer.destroy).not.toHaveBeenCalled();
		expect(mockNamespace.Player).toHaveBeenCalledTimes(1);
	});

	it('tears down cleanly when media becomes null during rerender', async () => {
		const mockPlayer: MockYouTubePlayer = {
			destroy: vi.fn(),
			getPlayerState: vi.fn(() => 1),
			pauseVideo: vi.fn(),
			playVideo: vi.fn(),
			seekTo: vi.fn()
		};

		const mockNamespace = {
			PlayerState: {
				BUFFERING: 3,
				PLAYING: 1
			},
			Player: vi.fn(
				(
					_element: HTMLDivElement,
					options: {
						events?: {
							onReady?: () => void;
							onStateChange?: (event: { data: number }) => void;
						};
					}
				) => {
					queueMicrotask(() => {
						options.events?.onReady?.();
					});
					return mockPlayer;
				}
			)
		};

		window.YT = mockNamespace as unknown as YouTubeNamespace;
		vi.mocked(loadYouTubeIframeApi).mockResolvedValue(mockNamespace as unknown as YouTubeNamespace);

		const view = render(YouTubePlayer, {
			media: TEST_MEDIA,
			shouldPauseMedia: false,
			shouldResumePausedMedia: false
		});

		await flushEffects();

		await expect(
			view.rerender({
				media: null,
				shouldPauseMedia: false,
				shouldResumePausedMedia: false
			})
		).resolves.toBeUndefined();
		await flushEffects();

		expect(mockPlayer.destroy).toHaveBeenCalledTimes(1);
	});
});
