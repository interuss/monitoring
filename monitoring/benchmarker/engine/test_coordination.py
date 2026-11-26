from monitoring.benchmarker.engine.coordination import (
    CoordinationGroupID,
    CoordinationMessage,
    CoordinationSubscriber,
    Coordinator,
)

GROUP = CoordinationGroupID("group")
ADD = "add"
REMOVE = "remove"


class _Subscriber(CoordinationSubscriber):
    def __init__(self):
        self.received: list[tuple[str, str]] = []

    def receive_coordination_message(self, msg: CoordinationMessage) -> None:
        self.received.append((msg.subject, msg.content))


# This test is AI-generated and has not been closely inspected by a human.
def test_cancelled_messages_are_not_replayed_to_new_subscribers():
    coordinator = Coordinator([GROUP])
    existing = _Subscriber()
    coordinator.subscribe(existing, GROUP)

    coordinator.publish(GROUP, ADD, "a")
    coordinator.publish(GROUP, ADD, "b")
    coordinator.publish(GROUP, REMOVE, "a", cancels=ADD)

    new = _Subscriber()
    coordinator.subscribe(new, GROUP)

    assert existing.received == [(ADD, "a"), (ADD, "b"), (REMOVE, "a")]
    assert new.received == [(ADD, "b")]


# This test is AI-generated and has not been closely inspected by a human.
def test_uncancelled_messages_are_replayed_to_new_subscribers():
    coordinator = Coordinator([GROUP])

    coordinator.publish(GROUP, ADD, "a")
    coordinator.publish(GROUP, REMOVE, "a")
    coordinator.publish(GROUP, ADD, "a")

    new = _Subscriber()
    coordinator.subscribe(new, GROUP)

    assert new.received == [(REMOVE, "a"), (ADD, "a")]
