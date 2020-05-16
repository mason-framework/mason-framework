"""Test flow scenarios."""

import time

import asyncmock
import pytest

import mason


@pytest.mark.asyncio
async def test_merge_node():
    bp = mason.Blueprint()
    merge = bp.create('flow.Merge')

    for _ in range(10):
        sleep = bp.create('flow.Sleep', values={'seconds': 0.1})
        sleep['finished'].connect(merge.continue_)
        bp['triggered'].connect(sleep.sleep)

    printer = bp.create('log.Print', values={'message': 'Finished!'})

    with asyncmock.patch.object(printer,
                                'print_',
                                side_effect=printer.print_) as mock_print:
        merge['merged'].connect(printer.print_)
        start = time.time()
        await bp()
        elapsed = time.time() - start

    assert merge.continue_.connection_count == 10
    assert elapsed < 0.15
    mock_print.assert_called_once()
