/** Attach only while the main display is showing a started game. */
export function idleCursor(node: HTMLElement) {
	let timer: ReturnType<typeof setTimeout>;
	function reveal() {
		clearTimeout(timer);
		node.removeAttribute('data-cursor-idle');
		timer = setTimeout(() => node.setAttribute('data-cursor-idle', ''), 2000);
	}
	window.addEventListener('mousemove', reveal);
	window.addEventListener('mousedown', reveal);
	reveal();
	return {
		destroy() {
			clearTimeout(timer);
			window.removeEventListener('mousemove', reveal);
			window.removeEventListener('mousedown', reveal);
			node.removeAttribute('data-cursor-idle');
		}
	};
}
