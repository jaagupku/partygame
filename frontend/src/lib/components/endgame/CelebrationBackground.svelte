<script lang="ts">
	import { browser } from '$app/environment';
	import { onDestroy, onMount } from 'svelte';

	type CelebrationIntensity = 'ambient' | 'impact' | 'final';
	type FireworkConfig = {
		id: number;
		x: number;
		y: number;
		delay: number;
		hue: number;
		interval: number;
		scale: number;
		particleCount: number;
	};
	type Particle = {
		x: number;
		y: number;
		vx: number;
		vy: number;
		size: number;
		hue: number;
		life: number;
		maxLife: number;
		alpha: number;
	};

	type Props = {
		stage: string;
	};

	let { stage }: Props = $props();
	let canvas = $state<HTMLCanvasElement | null>(null);
	let backgroundElement = $state<HTMLDivElement | null>(null);
	let width = $state(0);
	let height = $state(0);
	let animationFrameId: number | null = null;
	let resizeObserver: ResizeObserver | null = null;
	let reducedMotionQuery: MediaQueryList | null = null;
	let reducedMotion = $state(false);
	let particles: Particle[] = [];
	let nextBurstTimes = new Map<number, number>();
	let lastFrameTime = 0;

	const intensity = $derived.by<CelebrationIntensity>(() => {
		if (stage === 'first_place') {
			return 'final';
		}
		if (stage === 'third_place' || stage === 'second_place') {
			return 'impact';
		}
		return 'ambient';
	});

	function randomFromSeed(seed: number) {
		const value = Math.sin(seed * 12.9898) * 43758.5453;
		return value - Math.floor(value);
	}

	function range(seed: number, min: number, max: number) {
		return min + randomFromSeed(seed) * (max - min);
	}

	const confettiPieces = Array.from({ length: 42 }, (_, index) => ({
		id: index,
		left: range(index + 1, 0, 100),
		width: range(index + 101, 0.42, 0.9),
		height: range(index + 201, 0.85, 1.7),
		radius: randomFromSeed(index + 301) > 0.48 ? '999px' : '0.12rem',
		duration: range(index + 401, 3.2, 5.5),
		delay: range(index + 501, -4.8, -0.1),
		drift: range(index + 601, -7.2, 7.2),
		spin: range(index + 701, 180, 900),
		hue: range(index + 801, 0, 360)
	}));

	const ambientFireworks: FireworkConfig[] = Array.from({ length: 5 }, (_, index) => ({
		id: index,
		x: range(index + 11, 10, 90),
		y: range(index + 21, 16, 58),
		delay: range(index + 31, 0.2, 3.2),
		hue: range(index + 41, 0, 360),
		interval: range(index + 51, 3.4, 4.4),
		scale: range(index + 61, 0.68, 0.9),
		particleCount: 22
	}));

	const impactFireworks: FireworkConfig[] = Array.from({ length: 8 }, (_, index) => ({
		id: index,
		x: range(index + 111, 8, 92),
		y: range(index + 121, 14, 62),
		delay: range(index + 131, 0, 2.9),
		hue: range(index + 141, 0, 360),
		interval: range(index + 151, 3.05, 3.7),
		scale: range(index + 161, 0.78, 1.18),
		particleCount: 36
	}));

	const finaleFireworks: FireworkConfig[] = Array.from({ length: 11 }, (_, index) => ({
		id: index,
		x: range(index + 211, 6, 94),
		y: range(index + 221, 12, 64),
		delay: range(index + 231, 0, 2.8),
		hue: range(index + 241, 0, 360),
		interval: range(index + 251, 2.9, 3.55),
		scale: range(index + 261, 0.84, 1.32),
		particleCount: 44
	}));

	const fireworks = $derived(
		intensity === 'final'
			? finaleFireworks
			: intensity === 'impact'
				? impactFireworks
				: ambientFireworks
	);

	function configureCanvas() {
		const context = canvas?.getContext('2d');
		if (!canvas || !context) {
			return;
		}
		const ratio = Math.min(window.devicePixelRatio || 1, 2);
		canvas.width = Math.max(1, Math.floor(width * ratio));
		canvas.height = Math.max(1, Math.floor(height * ratio));
		canvas.style.width = `${width}px`;
		canvas.style.height = `${height}px`;
		context.setTransform(ratio, 0, 0, ratio, 0, 0);
	}

	function resetFireworkSchedule(now: number) {
		nextBurstTimes = new Map(fireworks.map((firework) => [firework.id, now + firework.delay]));
	}

	function spawnBurst(firework: FireworkConfig, now: number) {
		const originX = (firework.x / 100) * width;
		const originY = (firework.y / 100) * height;
		for (let index = 0; index < firework.particleCount; index += 1) {
			const seed = firework.id * 997 + index * 31 + Math.floor(now * 10);
			const angle = (Math.PI * 2 * index) / firework.particleCount + range(seed, -0.22, 0.22);
			const speed = range(seed + 1, 82, 220) * firework.scale;
			const life = range(seed + 2, 0.72, 1.22);
			particles.push({
				x: originX,
				y: originY,
				vx: Math.cos(angle) * speed,
				vy: Math.sin(angle) * speed - range(seed + 3, 8, 36),
				size: range(seed + 4, 1.4, 4.8) * firework.scale,
				hue: firework.hue + range(seed + 5, -38, 126),
				life,
				maxLife: life,
				alpha: 1
			});
		}
	}

	function drawFrame(timestamp: number) {
		if (!canvas || reducedMotion || width <= 0 || height <= 0) {
			return;
		}
		const context = canvas.getContext('2d');
		if (!context) {
			return;
		}
		const now = timestamp / 1000;
		const dt = Math.min(Math.max(now - lastFrameTime, 0), 0.04);
		lastFrameTime = now;

		context.clearRect(0, 0, width, height);
		context.globalCompositeOperation = 'lighter';

		for (const firework of fireworks) {
			const nextBurst = nextBurstTimes.get(firework.id) ?? now + firework.delay;
			if (now >= nextBurst) {
				spawnBurst(firework, now);
				nextBurstTimes.set(firework.id, now + firework.interval);
			}
		}

		particles = particles.filter((particle) => particle.life > 0);
		for (const particle of particles) {
			particle.life -= dt;
			particle.vx *= 0.985;
			particle.vy = particle.vy * 0.985 + 72 * dt;
			particle.x += particle.vx * dt;
			particle.y += particle.vy * dt;
			particle.alpha = Math.max(0, particle.life / particle.maxLife);

			const glowSize = particle.size * (1.8 + (1 - particle.alpha) * 1.5);
			context.beginPath();
			context.fillStyle = `hsla(${particle.hue}, 92%, 62%, ${particle.alpha * 0.24})`;
			context.arc(particle.x, particle.y, glowSize, 0, Math.PI * 2);
			context.fill();

			context.beginPath();
			context.fillStyle = `hsla(${particle.hue}, 94%, 64%, ${particle.alpha})`;
			context.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
			context.fill();
		}

		context.globalCompositeOperation = 'source-over';
		animationFrameId = requestAnimationFrame(drawFrame);
	}

	function startAnimation() {
		if (!browser || reducedMotion || animationFrameId !== null || width <= 0 || height <= 0) {
			return;
		}
		lastFrameTime = performance.now() / 1000;
		resetFireworkSchedule(lastFrameTime);
		animationFrameId = requestAnimationFrame(drawFrame);
	}

	function stopAnimation() {
		if (animationFrameId !== null) {
			cancelAnimationFrame(animationFrameId);
			animationFrameId = null;
		}
		particles = [];
		canvas?.getContext('2d')?.clearRect(0, 0, width, height);
	}

	$effect(() => {
		fireworks;
		if (!browser) {
			return;
		}
		resetFireworkSchedule(performance.now() / 1000);
	});

	$effect(() => {
		width;
		height;
		configureCanvas();
		stopAnimation();
		startAnimation();
	});

	$effect(() => {
		reducedMotion;
		if (reducedMotion) {
			stopAnimation();
			return;
		}
		startAnimation();
	});

	onMount(() => {
		reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
		reducedMotion = reducedMotionQuery.matches;
		const handleReducedMotionChange = () => {
			reducedMotion = Boolean(reducedMotionQuery?.matches);
		};
		reducedMotionQuery.addEventListener('change', handleReducedMotionChange);
		resizeObserver = new ResizeObserver((entries) => {
			const rect = entries[0]?.contentRect;
			if (!rect) {
				return;
			}
			width = rect.width;
			height = rect.height;
		});
		if (backgroundElement) {
			resizeObserver.observe(backgroundElement);
		}
		return () => {
			reducedMotionQuery?.removeEventListener('change', handleReducedMotionChange);
			resizeObserver?.disconnect();
			stopAnimation();
		};
	});

	onDestroy(() => {
		stopAnimation();
	});
</script>

<div
	class={`celebration-background celebration-${intensity}`}
	aria-hidden="true"
	bind:this={backgroundElement}
>
	<div class="celebration-glow"></div>
	<canvas class="fireworks-canvas" bind:this={canvas}></canvas>
	<div class="confetti">
		{#each confettiPieces as piece (piece.id)}
			<span
				style={`--confetti-left:${piece.left}%;--confetti-width:${piece.width}rem;--confetti-height:${piece.height}rem;--confetti-radius:${piece.radius};--confetti-duration:${piece.duration}s;--confetti-delay:${piece.delay}s;--confetti-drift:${piece.drift}rem;--confetti-spin:${piece.spin}deg;--confetti-hue:${piece.hue};`}
			></span>
		{/each}
	</div>
</div>

<style>
	.celebration-background {
		position: absolute;
		inset: 0;
		z-index: 0;
		pointer-events: none;
		overflow: hidden;
	}

	.celebration-glow {
		position: absolute;
		inset: -20%;
		background:
			radial-gradient(circle at 22% 18%, rgb(250 204 21 / 0.28), transparent 18%),
			radial-gradient(circle at 78% 22%, rgb(56 189 248 / 0.24), transparent 20%),
			radial-gradient(circle at 50% 72%, rgb(244 114 182 / 0.18), transparent 22%);
		animation: celebration-glow 5.4s ease-in-out infinite alternate;
	}

	.celebration-final .celebration-glow {
		opacity: 1.15;
	}

	.fireworks-canvas {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
	}

	.confetti span {
		position: absolute;
		top: -12%;
		left: var(--confetti-left);
		width: var(--confetti-width);
		height: var(--confetti-height);
		border-radius: var(--confetti-radius);
		opacity: 0.9;
		background: hsl(calc(var(--confetti-hue) * 1deg) 85% 62%);
		animation: fall var(--confetti-duration) linear infinite;
		animation-delay: var(--confetti-delay);
		transform: rotate(var(--confetti-spin));
	}

	.celebration-ambient .confetti span:nth-child(n + 25) {
		display: none;
	}

	@keyframes fall {
		0% {
			transform: translate3d(0, 0, 0) rotate(0deg);
		}
		100% {
			transform: translate3d(var(--confetti-drift), 115vh, 0) rotate(var(--confetti-spin));
		}
	}

	@keyframes celebration-glow {
		from {
			transform: translate3d(-1.2%, -0.8%, 0) scale(1);
			opacity: 0.72;
		}

		to {
			transform: translate3d(1.2%, 0.8%, 0) scale(1.04);
			opacity: 1;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.celebration-glow,
		.confetti span {
			animation: none;
		}

		.fireworks-canvas {
			display: none;
		}
	}
</style>
