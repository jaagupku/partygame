<script lang="ts">
	import { goto } from '$app/navigation';
	import { currentUser } from '$lib/auth-store';
	import { messages } from '$lib/i18n';
	import { showErrorToast } from '$lib/toast-store';

	let email = $state('');
	let password = $state('');
	let loading = $state(false);

	async function submit() {
		loading = true;
		const response = await fetch('/api/v1/auth/login', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email, password })
		});
		loading = false;
		if (!response.ok) {
			showErrorToast($messages.auth.loginFailed);
			return;
		}
		currentUser.set(await response.json());
		goto('/definitions');
	}
</script>

<svelte:head>
	<title>{$messages.auth.login} | {$messages.common.appName}</title>
</svelte:head>

<section class="card mx-auto max-w-xl stack-md">
	<div>
		<h1 class="page-title text-left">{$messages.auth.login}</h1>
		<p class="page-subtitle text-left">{$messages.auth.loginSubtitle}</p>
	</div>
	<form class="stack-md" onsubmit={(event) => (event.preventDefault(), submit())}>
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
				autocomplete="current-password"
				required
			/>
		</label>
		<button class="btn btn-primary text-lg" disabled={loading} type="submit">
			{loading ? $messages.common.loading : $messages.auth.login}
		</button>
	</form>
	<button class="btn btn-ghost" type="button" onclick={() => goto('/signup')}>
		{$messages.auth.needAccount}
	</button>
</section>
