"""
Base test classes for CV-Tailor tests.

Provides AsyncTestCase with proper event loop management to fix async testing issues.
"""

import asyncio
from django.test import TestCase, TransactionTestCase


class AsyncTestCase(TestCase):
    """
    Base test case for async Django tests with proper event loop management.

    Fixes issues like:
    - RuntimeError: '<Queue> is bound to a different event loop'
    - Coroutines not being awaited
    - Event loop conflicts between tests

    Usage:
        class MyAsyncTests(AsyncTestCase):
            async def test_something_async(self):
                result = await some_async_function()
                self.assertEqual(result, expected)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._async_loop = None

    def setUp(self):
        """Set up a new event loop for each test."""
        super().setUp()
        # Create a new event loop for this test
        self._async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._async_loop)

    def tearDown(self):
        """Clean up the event loop after each test."""
        super().tearDown()
        if self._async_loop:
            # Close all pending tasks
            pending = asyncio.all_tasks(self._async_loop)
            for task in pending:
                task.cancel()

            # Run the loop one more time to process cancellations
            if pending:
                self._async_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

            # Close the loop
            self._async_loop.close()
            self._async_loop = None

    def run_async(self, coro):
        """
        Helper to run async functions in tests.

        Usage:
            def test_something(self):
                result = self.run_async(async_function())
                self.assertEqual(result, expected)
        """
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        return self._async_loop.run_until_complete(coro)


class AsyncTransactionTestCase(TransactionTestCase):
    """
    Async test case with database transaction rollback support.

    Use this when you need full database transaction isolation.
    Slower than AsyncTestCase but provides true transaction rollback.

    Usage:
        class MyAsyncTransactionTests(AsyncTransactionTestCase):
            async def test_with_db_transactions(self):
                # Each test runs in a transaction that gets rolled back
                result = await async_db_operation()
                self.assertTrue(result)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._async_loop = None

    def setUp(self):
        """Set up a new event loop for each test."""
        super().setUp()
        self._async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._async_loop)

    def tearDown(self):
        """Clean up the event loop after each test."""
        super().tearDown()
        if self._async_loop:
            # Close all pending tasks
            pending = asyncio.all_tasks(self._async_loop)
            for task in pending:
                task.cancel()

            if pending:
                self._async_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

            self._async_loop.close()
            self._async_loop = None

    def run_async(self, coro):
        """Helper to run async functions in tests."""
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        return self._async_loop.run_until_complete(coro)
