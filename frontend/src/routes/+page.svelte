<script lang="ts">
	import { goto } from '$app/navigation';
</script>

<h1 class="page-title">Party Quiz Arena</h1>
<p class="page-subtitle">Pick how you want to enter the game.</p>

<div class="stack-lg">
	<button class="btn btn-primary min-h-24 text-3xl md:text-4xl" onclick={() => goto('/create')}>
		Create
	</button>
	<button class="btn btn-accent min-h-24 text-3xl md:text-4xl" onclick={() => goto('/play')}>
		Join
	</button>
</div>
