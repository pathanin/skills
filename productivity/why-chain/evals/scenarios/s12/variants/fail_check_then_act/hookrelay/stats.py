class Stats:
    """Per-event-type count of handler runs."""

    def __init__(self):
        self._by_type = {}

    def record(self, event_type):
        self._by_type[event_type] = self._by_type.get(event_type, 0) + 1

    def count_for(self, event_type):
        return self._by_type.get(event_type, 0)

    def snapshot(self):
        return dict(self._by_type)
