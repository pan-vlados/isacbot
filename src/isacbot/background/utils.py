import asyncio
import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from asyncio import Task
    from collections.abc import Awaitable, Callable


logger = logging.getLogger(__name__)


# As noted in [documentation](https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task):
# We should save a reference to tasks passed to function `create_task`, to avoid a task
# disappearing mid-execution. The event loop only keeps weak references to tasks. A task
# that isn’t referenced elsewhere may get garbage collected at any time, even before
# it’s done.
BACKGROUND_TASKS: set['Task'] = set()


async def _delay_task(
    task: 'Callable[[], Awaitable[Any]]', delay: int, *args: Any, **kwargs: Any
) -> 'Awaitable[Any]':
    await asyncio.sleep(delay=delay)
    return await task(*args, **kwargs)


async def create_delayed_background_task(
    *, task: 'Callable[[], Awaitable[Any]]', delay: int, **kwargs: Any
) -> 'Awaitable[Any]':
    """Create delayed background task using `asyncio.sleep` and don't block
    current event loop.
    """
    background_task: Task = asyncio.create_task(_delay_task(task=task, delay=delay, **kwargs))
    # The log message not only means that the task has been scheduled,
    # but also that it can be completed because it is already running.
    logger.debug('%s scheduled for %d seconds.' % (background_task.get_name(), delay))

    # Add task to the set. This creates a strong reference.
    BACKGROUND_TASKS.add(background_task)

    # To prevent keeping references to finished tasks forever,
    # make each task remove its own reference from the set after
    # completion:
    background_task.add_done_callback(BACKGROUND_TASKS.discard)
    return background_task
