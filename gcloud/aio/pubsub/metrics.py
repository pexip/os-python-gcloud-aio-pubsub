from __future__ import annotations

from contextlib import contextmanager
from timeit import default_timer
from typing import Any
from typing import Iterator

from gcloud.aio.auth import BUILD_GCLOUD_REST
from typing_extensions import Self

if BUILD_GCLOUD_REST:  # pylint: disable=too-complex
    pass
else:
    from aioprometheus import (  # type: ignore[attr-defined]
        Counter as _Counter,
        Histogram as _Histogram,
    )

    _NAMESPACE = 'gcloud_aio'
    _SUBSYSTEM = 'pubsub'

    class _AioShim:
        def __init__(self, cls: type[_Counter | _Histogram],
                     name: str, doc: str, **kwargs: Any) -> None:
            self._wrapped = cls(name=self._full_name(name), doc=doc, **kwargs)
            self._labels: dict[str, str] = {}

        @staticmethod
        def _full_name(name: str, unit: str = '') -> str:
            return '_'.join(part for part in (
                _NAMESPACE, _SUBSYSTEM, name, unit) if part)

        def labels(self, **labels: str) -> Self:
            self._labels.update(labels)
            return self

    class Counter(_AioShim):
        def __init__(self, name: str, doc: str, **kwargs: Any) -> None:
            super().__init__(_Counter, name, doc, **kwargs)
            self._wrapped: _Counter

        def inc(self, value: float = 1) -> None:
            self._wrapped.add(self._labels, value)

    class Histogram(_AioShim):
        def __init__(self, name: str, doc: str, **kwargs: Any) -> None:
            super().__init__(_Histogram, name, doc, **kwargs)
            self._wrapped: _Histogram

        def observe(self, value: float) -> None:
            self._wrapped.observe(self._labels, value)

        @contextmanager
        def time(self) -> Iterator[None]:
            start = default_timer()
            yield None
            # Time can go backwards.
            duration = max(default_timer() - start, 0)
            self._wrapped.observe(self._labels, duration)

    BATCH_SIZE = Histogram(
        'subscriber_batch',
        'Histogram of number of messages pulled in a single batch',
        buckets=(
            0, 1, 5, 10, 25, 50, 100, 150, 250, 500, 1000, 1500, 2000,
            5000, float('inf'),
        ),
    )

    CONSUME = Counter(
        'subscriber_consume',
        'Counter of the outcomes of PubSub message consume attempts',
    )

    CONSUME_LATENCY = Histogram(
        'subscriber_consume_latency',
        'Histogram of PubSub message consume latencies',
        buckets=(.01, .1, .25, .5, 1.0, 2.5, 5.0, 7.5, 10.0, 20.0,
                 30.0, 60.0, 120.0, float('inf')),
    )

    BATCH_STATUS = Counter(
        'subscriber_batch_status',
        'Counter for success/failure to process PubSub message batches',
    )

    MESSAGES_PROCESSED = Counter(
        'subscriber_messages_processed',
        'Counter of successfully acked/nacked messages',
    )

    MESSAGES_RECEIVED = Counter(
        'subscriber_messages_received',
        'Counter of messages pulled from subscription',
    )
