<script lang="ts">
	import { tick } from 'svelte';
	import { messages } from '$lib/i18n';

	type Props = {
		step: StepDefinition;
	};

	let { step }: Props = $props();
	let textarea: HTMLTextAreaElement;

	const actions = [
		{ icon: 'B', title: 'Bold', run: () => wrapSelection('**', '**') },
		{ icon: 'I', title: 'Italic', run: () => wrapSelection('_', '_') },
		{ icon: 'H2', title: 'Large text', run: () => prefixLines('## ') },
		{ icon: '*', title: 'Bullet list', run: () => prefixLines('- ') },
		{ icon: '>', title: 'Quote', run: () => prefixLines('> ') },
		{ icon: 'Tx', title: 'Clear formatting', run: clearFormatting }
	];

	function bodyText() {
		return step.body ?? '';
	}

	async function replaceBody(
		nextText: string,
		selectionStart: number,
		selectionEnd: number = selectionStart
	) {
		step.body = nextText;
		await tick();
		textarea.focus();
		textarea.setSelectionRange(selectionStart, selectionEnd);
	}

	function getSelectedRange() {
		return {
			start: textarea.selectionStart,
			end: textarea.selectionEnd
		};
	}

	function getLineRange(text: string, start: number, end: number) {
		const lineStart = text.lastIndexOf('\n', Math.max(0, start - 1)) + 1;
		let lineEnd = text.indexOf('\n', end);
		if (lineEnd === -1) {
			lineEnd = text.length;
		}
		return { lineStart, lineEnd };
	}

	function wrapSelection(prefix: string, suffix: string) {
		const text = bodyText();
		const { start, end } = getSelectedRange();
		const selected = text.slice(start, end);
		const replacement = `${prefix}${selected}${suffix}`;
		const nextText = `${text.slice(0, start)}${replacement}${text.slice(end)}`;
		const cursorStart = selected ? start : start + prefix.length;
		const cursorEnd = selected ? start + replacement.length : cursorStart;
		void replaceBody(nextText, cursorStart, cursorEnd);
	}

	function prefixLines(prefix: string) {
		const text = bodyText();
		const { start, end } = getSelectedRange();
		const { lineStart, lineEnd } = getLineRange(text, start, end);
		const selectedLines = text.slice(lineStart, lineEnd);
		const prefixedLines = selectedLines
			.split('\n')
			.map((line) => {
				if (!line.trim()) {
					return line;
				}
				return line.startsWith(prefix) ? line : `${prefix}${line}`;
			})
			.join('\n');
		const nextText = `${text.slice(0, lineStart)}${prefixedLines}${text.slice(lineEnd)}`;
		const addedLength = prefixedLines.length - selectedLines.length;
		void replaceBody(
			nextText,
			start + (start === lineStart ? prefix.length : 0),
			end + addedLength
		);
	}

	function clearFormatting() {
		const text = bodyText();
		const { start, end } = getSelectedRange();
		const range =
			start === end ? getLineRange(text, start, end) : { lineStart: start, lineEnd: end };
		const selected = text.slice(range.lineStart, range.lineEnd);
		const cleaned = selected
			.split('\n')
			.map((line) =>
				line
					.replace(/^(\s*)(#{1,6}\s+|[-*]\s+|>\s+)/, '$1')
					.replace(/\*\*([^*]+)\*\*/g, '$1')
					.replace(/_([^_]+)_/g, '$1')
			)
			.join('\n');
		const nextText = `${text.slice(0, range.lineStart)}${cleaned}${text.slice(range.lineEnd)}`;
		void replaceBody(nextText, range.lineStart, range.lineStart + cleaned.length);
	}
</script>

<label class="input-wrap">
	<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
		{$messages.editor.body}
	</span>
	<div class="flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-slate-50/80 p-2">
		{#each actions as action}
			<button
				type="button"
				class="inline-flex h-8 min-w-8 items-center justify-center rounded-xl border border-slate-200 bg-white px-2 text-sm font-black text-slate-700 shadow-sm hover:border-sky-300 hover:text-sky-700"
				title={action.title}
				aria-label={action.title}
				onclick={action.run}
			>
				{action.icon}
			</button>
		{/each}
	</div>
	<textarea
		bind:this={textarea}
		bind:value={step.body}
		class="input min-h-32 text-lg"
		placeholder={$messages.editor.bodyPlaceholder}
	></textarea>
</label>
