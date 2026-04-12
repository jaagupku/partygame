const YOUTUBE_HOSTS = new Set([
	'youtube.com',
	'www.youtube.com',
	'm.youtube.com',
	'youtu.be',
	'www.youtu.be',
	'www.youtube-nocookie.com',
	'youtube-nocookie.com'
]);

const VIDEO_ID_PATTERN = /^[A-Za-z0-9_-]{11}$/;
let youtubeIframeApiPromise: Promise<YouTubeNamespace> | null = null;

export type YouTubeMedia = {
	videoId: string;
	embedUrl: string;
	startSeconds: number;
};

function isValidVideoId(value: string): boolean {
	return VIDEO_ID_PATTERN.test(value);
}

function normalizeVideoId(value: string | undefined): string | null {
	const trimmed = value?.trim() ?? '';
	return isValidVideoId(trimmed) ? trimmed : null;
}

function parseTimeToken(value: string | null | undefined): number {
	const trimmed = value?.trim() ?? '';
	if (!trimmed) {
		return 0;
	}

	if (/^\d+$/.test(trimmed)) {
		return Number.parseInt(trimmed, 10);
	}

	const matches = [...trimmed.matchAll(/(\d+)(h|m|s)/gi)];
	if (matches.length === 0) {
		return 0;
	}

	return matches.reduce((total, [, amount, unit]) => {
		const numericAmount = Number.parseInt(amount, 10);
		if (unit.toLowerCase() === 'h') {
			return total + numericAmount * 3600;
		}
		if (unit.toLowerCase() === 'm') {
			return total + numericAmount * 60;
		}
		return total + numericAmount;
	}, 0);
}

function getYouTubeStartSeconds(url: URL): number {
	const queryValue = url.searchParams.get('start') ?? url.searchParams.get('t');
	if (queryValue) {
		return parseTimeToken(queryValue);
	}
	const hash = url.hash.replace(/^#/, '');
	const hashParams = new URLSearchParams(hash);
	return parseTimeToken(hashParams.get('t') ?? hashParams.get('start'));
}

export function getYouTubeVideoId(src: string): string | null {
	if (!src.trim()) {
		return null;
	}

	try {
		const url = new URL(src);
		const hostname = url.hostname.toLowerCase();
		if (!YOUTUBE_HOSTS.has(hostname)) {
			return null;
		}

		if (hostname.includes('youtu.be')) {
			return normalizeVideoId(url.pathname.split('/').filter(Boolean)[0]);
		}

		const pathSegments = url.pathname.split('/').filter(Boolean);
		if (pathSegments[0] === 'watch') {
			return normalizeVideoId(url.searchParams.get('v') ?? undefined);
		}
		if (pathSegments[0] === 'embed' || pathSegments[0] === 'shorts' || pathSegments[0] === 'live') {
			return normalizeVideoId(pathSegments[1]);
		}
		if (pathSegments[0] === 'v') {
			return normalizeVideoId(pathSegments[1]);
		}
		return normalizeVideoId(url.searchParams.get('v') ?? undefined);
	} catch {
		return normalizeVideoId(src);
	}
}

export function isYouTubeUrl(src: string): boolean {
	return getYouTubeVideoId(src) !== null;
}

export function buildYouTubeEmbedUrl(
	videoId: string,
	options: {
		autoplay?: boolean;
		loop?: boolean;
		origin?: string;
		startSeconds?: number;
		controls?: boolean;
	} = {}
): string {
	const url = new URL(`https://www.youtube-nocookie.com/embed/${videoId}`);
	url.searchParams.set('enablejsapi', '1');
	url.searchParams.set('playsinline', '1');
	url.searchParams.set('rel', '0');
	url.searchParams.set('iv_load_policy', '3');
	url.searchParams.set('fs', '0');
	url.searchParams.set('modestbranding', '0');
	url.searchParams.set('controls', options.controls ? '1' : '0');
	if (options.autoplay) {
		url.searchParams.set('autoplay', '1');
	}
	if (options.loop) {
		url.searchParams.set('loop', '1');
		url.searchParams.set('playlist', videoId);
	}
	if (options.origin) {
		url.searchParams.set('origin', options.origin);
	}
	if (options.startSeconds && options.startSeconds > 0) {
		url.searchParams.set('start', String(Math.floor(options.startSeconds)));
	}
	return url.toString();
}

export function getYouTubeMedia(
	src: string,
	options: Parameters<typeof buildYouTubeEmbedUrl>[1] = {}
): YouTubeMedia | null {
	if (!src.trim()) {
		return null;
	}

	try {
		const url = new URL(src);
		const videoId = getYouTubeVideoId(src);
		if (!videoId) {
			return null;
		}
		const startSeconds = options.startSeconds ?? getYouTubeStartSeconds(url);
		return {
			videoId,
			startSeconds,
			embedUrl: buildYouTubeEmbedUrl(videoId, {
				...options,
				startSeconds
			})
		};
	} catch {
		const videoId = getYouTubeVideoId(src);
		if (!videoId) {
			return null;
		}
		const startSeconds = options.startSeconds ?? 0;
		return {
			videoId,
			startSeconds,
			embedUrl: buildYouTubeEmbedUrl(videoId, {
				...options,
				startSeconds
			})
		};
	}
}

export function loadYouTubeIframeApi(): Promise<YouTubeNamespace> {
	if (typeof window === 'undefined') {
		return Promise.reject(new Error('YouTube IFrame API is only available in the browser.'));
	}
	if (window.YT?.Player) {
		return Promise.resolve(window.YT);
	}
	if (youtubeIframeApiPromise) {
		return youtubeIframeApiPromise;
	}

	youtubeIframeApiPromise = new Promise((resolve) => {
		const previousReady = window.onYouTubeIframeAPIReady;
		window.onYouTubeIframeAPIReady = () => {
			previousReady?.();
			if (window.YT) {
				resolve(window.YT);
			}
		};

		const existingScript = document.querySelector<HTMLScriptElement>(
			'script[src="https://www.youtube.com/iframe_api"]'
		);
		if (existingScript) {
			return;
		}

		const script = document.createElement('script');
		script.src = 'https://www.youtube.com/iframe_api';
		script.async = true;
		document.head.appendChild(script);
	});

	return youtubeIframeApiPromise;
}
