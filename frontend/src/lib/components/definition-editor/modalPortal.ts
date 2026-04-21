let activePortalCount = 0;

export function modalPortal(node: HTMLElement) {
	document.body.appendChild(node);
	activePortalCount += 1;
	document.body.classList.add('modal-open');

	return {
		destroy() {
			activePortalCount = Math.max(0, activePortalCount - 1);
			if (activePortalCount === 0) {
				document.body.classList.remove('modal-open');
			}
			node.remove();
		}
	};
}
