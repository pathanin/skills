from .handlers import default_registry
from .receipts import ReceiptLog, receipt_for
from .stats import Stats


class Relay:
    def __init__(self, registry=None, receipts=None, stats=None):
        self.registry = registry if registry is not None else default_registry()
        self.receipts = receipts if receipts is not None else ReceiptLog()
        self.stats = stats if stats is not None else Stats()

    def handle(self, event):
        handler = self.registry.handler_for(event.type)
        result = handler(event)
        receipt = receipt_for(event, result)
        self.receipts.add(receipt)
        self.stats.record(event.type)
        return receipt
