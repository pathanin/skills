import threading

from .handlers import default_registry
from .receipts import ReceiptLog, receipt_for
from .stats import Stats


class Relay:
    def __init__(self, registry=None, receipts=None, stats=None):
        self.registry = registry if registry is not None else default_registry()
        self.receipts = receipts if receipts is not None else ReceiptLog()
        self.stats = stats if stats is not None else Stats()
        self._cond = threading.Condition()
        self._inflight = set()

    def handle(self, event):
        with self._cond:
            while True:
                receipt = self.receipts.get(event.id)
                if receipt is not None:
                    return receipt
                if event.id not in self._inflight:
                    self._inflight.add(event.id)
                    break
                self._cond.wait()

        try:
            handler = self.registry.handler_for(event.type)
            result = handler(event)
            receipt = receipt_for(event, result)
            self.receipts.add(receipt)
            self.stats.record(event.type)
            return receipt
        finally:
            with self._cond:
                self._inflight.discard(event.id)
                self._cond.notify_all()
