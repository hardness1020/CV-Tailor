"""
Test utility functions for CV-Tailor tests.

Provides helper functions to validate async behavior and prevent silent test failures.
"""

import asyncio
import inspect
from typing import Any, Coroutine
from unittest.mock import AsyncMock


def assert_awaited(obj: Any) -> None:
    """
    Assert that an async function was properly awaited.

    Raises AssertionError if:
    - A coroutine object was returned but not awaited
    - An AsyncMock was not awaited

    Usage:
        # This will raise AssertionError
        result = async_function()  # Forgot await
        assert_awaited(result)

        # This will pass
        result = await async_function()
        assert_awaited(result)
    """
    if inspect.iscoroutine(obj):
        raise AssertionError(
            f"Coroutine {obj} was not awaited. Did you forget 'await'?"
        )

    if isinstance(obj, AsyncMock):
        if obj.await_count == 0:
            raise AssertionError(
                f"AsyncMock {obj} was not awaited"
            )


def is_coroutine_function(func: Any) -> bool:
    """Check if a function is a coroutine function (async def)."""
    return asyncio.iscoroutinefunction(func)


def run_sync(coro: Coroutine) -> Any:
    """
    Run an async coroutine synchronously in a new event loop.

    Useful for running async code in sync test methods.

    Usage:
        def test_something(self):
            result = run_sync(async_function())
            self.assertEqual(result, expected)
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        # Clean up pending tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        loop.close()


def create_async_mock(return_value: Any = None, side_effect: Any = None) -> AsyncMock:
    """
    Create an AsyncMock with proper configuration.

    Args:
        return_value: Value to return when awaited
        side_effect: Side effect (can be exception or iterable of values)

    Usage:
        mock_service = create_async_mock(return_value=EnrichedArtifactResult(...))
        mock_service.preprocess_multi_source_artifact = create_async_mock(
            side_effect=EnrichmentError("Test error")
        )
    """
    mock = AsyncMock()
    if return_value is not None:
        mock.return_value = return_value
    if side_effect is not None:
        mock.side_effect = side_effect
    return mock


class AsyncContextManagerMock:
    """
    Mock for async context managers.

    Usage:
        async with AsyncContextManagerMock() as mock:
            # mock.__aenter__ was called
            pass
        # mock.__aexit__ was called
    """

    def __init__(self, return_value: Any = None):
        self.return_value = return_value
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.exited = True
        return False


def assert_no_pending_tasks(loop: asyncio.AbstractEventLoop = None) -> None:
    """
    Assert that there are no pending async tasks in the event loop.

    Helps catch async tasks that weren't awaited or cleaned up.

    Usage:
        def tearDown(self):
            assert_no_pending_tasks(self._async_loop)
            super().tearDown()
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    pending = [task for task in asyncio.all_tasks(loop) if not task.done()]

    if pending:
        task_names = [str(task) for task in pending]
        raise AssertionError(
            f"Found {len(pending)} pending async tasks:\n" + "\n".join(task_names)
        )
