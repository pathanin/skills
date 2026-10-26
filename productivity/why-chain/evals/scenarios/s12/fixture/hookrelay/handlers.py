class UnknownEventType(KeyError):
    """Raised when no handler is registered for a delivery."""


class HandlerRegistry:
    def __init__(self):
        self._handlers = {}

    def register(self, event_type, handler):
        self._handlers[event_type] = handler
        return handler

    def handler_for(self, event_type):
        try:
            return self._handlers[event_type]
        except KeyError:
            raise UnknownEventType(event_type) from None

    def types(self):
        return sorted(self._handlers)


def _ping(event):
    return {"pong": True}


def _deploy(event):
    service = event.payload.get("service")
    return {"service": service, "status": "queued"}


def default_registry():
    registry = HandlerRegistry()
    registry.register("ping", _ping)
    registry.register("deploy", _deploy)
    return registry
