"""Keep legacy provider tracking fields isolated per execution context."""
from contextvars import ContextVar


def tracked_field(name, default=None):
    def get(self):
        value = self._tracking_context().get().get(name, default)
        return dict(value) if isinstance(value, dict) else value

    def set_value(self, value):
        context = self._tracking_context()
        context.set({**context.get(), name: value})

    return property(get, set_value)


class RequestTracking:
    last_model_name = tracked_field('model')
    last_prompt_id = tracked_field('prompt_id')
    last_prompt_version = tracked_field('prompt_version')
    last_usage = tracked_field('usage', {})

    def _tracking_context(self):
        if '_request_tracking' not in self.__dict__:
            self._request_tracking = ContextVar('provider_tracking', default={})
        return self._request_tracking

    def reset_tracking(self):
        self._tracking_context().set({'model': self.model_name})
