import asyncio
from threading import Thread
from allma_model.core.event_bus import EventBus, BusEvent


def test_publish_from_thread_and_reuse_across_loops():
    bus = EventBus()
    seen = []
    async def consumer(event):
        seen.append(event.payload['value'])
        bus.stop()
    bus.register_consumer(consumer)
    for value in [1, 2]:
        thread = Thread(target=lambda: bus.publish_sync(BusEvent('test', {'value': value}, 'test')))
        thread.start()
        thread.join()
        async def run():
            await asyncio.wait_for(bus.consume_loop(), timeout=2)
        asyncio.run(run())
    assert seen == [1, 2]


def test_full_queue_returns_false():
    bus = EventBus(maxsize=1)
    event = BusEvent('test', {}, 'test')
    assert bus.publish_sync(event)
    assert not asyncio.run(bus.publish(event))
    assert bus.get_stats()['events_dropped'] == 1
