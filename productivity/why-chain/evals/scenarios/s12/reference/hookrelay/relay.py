import threading

from .handlers import default_registry
from .receipts import ReceiptLog, receipt_for
from .stats import Stats


class _Pending:
    """A claim on one event id while its handler is running."""

    def __init__(self):
        self.done = threading.Event()


class Relay:
    def __init__(self, registry=None, receipts=None, stats=None):
        self.registry = registry if registry is not None else default_registry()
        self.receipts = receipts if receipts is not None else ReceiptLog()
        self.stats = stats if stats is not None else Stats()
        self._lock = threading.Lock()
        self._pending = {}

    def handle(self, event):
        with self._lock:
            receipt = self.receipts.get(event.id)
            if receipt is not None:
                return receipt
            pending = self._pending.get(event.id)
            leader = pending is None
            if leader:
                pending = _Pending()
                self._pending[event.id] = pending

        if not leader:
            # Another delivery of this event is already running. Wait for it,
            # then re-enter so a failed first attempt can be retried here.
            pending.done.wait()
            return self.handle(event)

        try:
            return self._dispatch(event)
        finally:
            with self._lock:
                self._pending.pop(event.id, None)
            pending.done.set()

    def _dispatch(self, event):
        handler = self.registry.handler_for(event.type)
        result = handler(event)
        receipt = receipt_for(event, result)
        self.receipts.add(receipt)
        self.stats.record(event.type)
        return receipt
