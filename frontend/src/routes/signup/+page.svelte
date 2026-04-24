<script lang="ts">
	import { goto } from '$app/navigation';
	import { currentUser } from '$lib/auth-store';
	import { messages } from '$lib/i18n';

	let displayName = $state('');
	let email = $state('');
	let password = $state('');
	let loading = $state(false);
	let errorMessage = $state('');

	async function submit() {
		loading = true;
		errorMessage = '';
		const response = await fetch('/api/v1/auth/signup', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				display_name: displayName,
				email,
				password
			})
		});
		loading = false;
		if (!response.ok) {
			errorMessage = $messages.auth.signupFailed;
			return;
		}
		currentUser.set(await response.json());
		goto('/definitions');
	}
</script>

<svelte:head>
	<title>{$messages.auth.signup} | {$messages.common.appName}</title>
</svelte:head>

<section class="card mx-auto max-w-xl stack-md">
	<div>
		<h1 class="page-title text-left">{$messages.auth.signup}</h1>
		<p class="page-subtitle text-left">{$messages.auth.signupSubtitle}</p>
	</div>
	{#if errorMessage}
		<div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
			{errorMessage}
		</div>
	{/if}
	<form class="stack-md" onsubmit={(event) => (event.preventDefault(), submit())}>
		<label class="input-wrap">
			<span class="label-title">{$messages.auth.displayName}</span>
			<input bind:value={displayName} class="input text-lg" autocomplete="name" required />
		</label>
		<label class="input-wrap">
			<span class="label-title">{$messages.auth.email}</span>
			<input bind:value={email} class="input text-lg" type="email" autocomplete="email" required />
		</label>
		<label class="input-wrap">
			<span class="label-title">{$messages.auth.password}</span>
			<input
				bind:value={password}
				class="input text-lg"
				type="password"
				autocomplete="new-password"
				minlength="8"
				required
			/>
		</label>
		<button class="btn btn-primary text-lg" disabled={loading} type="submit">
			{loading ? $messages.common.loading : $messages.auth.signup}
		</button>
	</form>
	<button class="btn btn-ghost" type="button" onclick={() => goto('/login')}>
		{$messages.auth.haveAccount}
	</button>
</section>
