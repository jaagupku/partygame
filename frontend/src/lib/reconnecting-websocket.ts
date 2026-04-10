type ReconnectingWebSocketOptions = {
	onMessage?: (data: string) => void;
	onOpen?: () => void;
	onClose?: () => void;
	onStatusChange?: (connected: boolean) => void;
	initialDelayMs?: number;
	maxDelayMs?: number;
	backoffMultiplier?: number;
};

export function createReconnectingWebSocket(
	url: string,
	options: ReconnectingWebSocketOptions = {}
) {
	const initialDelayMs = options.initialDelayMs ?? 500;
	const maxDelayMs = options.maxDelayMs ?? 10_000;
	const backoffMultiplier = options.backoffMultiplier ?? 2;

	let websocket: WebSocket | null = null;
	let reconnectDelayMs = initialDelayMs;
	let reconnectTimeout: number | null = null;
	let closedManually = false;

	function updateStatus(connected: boolean) {
		options.onStatusChange?.(connected);
		if (connected) {
			options.onOpen?.();
		} else {
			options.onClose?.();
		}
	}

	function scheduleReconnect() {
		if (closedManually || reconnectTimeout !== null) {
			return;
		}
		reconnectTimeout = window.setTimeout(() => {
			reconnectTimeout = null;
			connect();
		}, reconnectDelayMs);
		reconnectDelayMs = Math.min(maxDelayMs, reconnectDelayMs * backoffMultiplier);
	}

	function connect() {
		if (closedManually) {
			return;
		}
		websocket = new WebSocket(url);
		websocket.onmessage = (event) => {
			options.onMessage?.(event.data);
		};
		websocket.onopen = () => {
			reconnectDelayMs = initialDelayMs;
			updateStatus(true);
		};
		websocket.onclose = () => {
			websocket = null;
			updateStatus(false);
			scheduleReconnect();
		};
		websocket.onerror = () => {
			websocket?.close();
		};
	}

	function send(payload: string) {
		if (websocket?.readyState !== WebSocket.OPEN) {
			return false;
		}
		websocket.send(payload);
		return true;
	}

	function close() {
		closedManually = true;
		if (reconnectTimeout !== null) {
			clearTimeout(reconnectTimeout);
			reconnectTimeout = null;
		}
		websocket?.close();
		websocket = null;
	}

	connect();

	return {
		send,
		close,
		get readyState() {
			return websocket?.readyState ?? WebSocket.CLOSED;
		}
	};
}
