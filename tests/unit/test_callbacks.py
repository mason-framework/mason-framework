"""Test the callback system."""
# pylint: disable=protected-access, missing-function-docstring

import asyncio
import gc

import asyncmock
import mock
import pytest

from mason import callbacks


def test_signal_creation_with_annotation_creates_signature():
    signal = callbacks.Signal(int)
    assert signal._annotations == (int,)
    assert signal._signature.parameters['arg_0'].annotation == int


def test_signal_cleanup_dead_refs_removes_references():
    signal = callbacks.Signal()
    mock_callback = mock.Mock()
    signal.connect(mock_callback)
    assert len(signal._slot_refs) == 1
    del mock_callback
    gc.collect()
    signal._cleanup_dead_refs()
    assert len(signal._slot_refs) == 0

def test_signal_get_active_slots_cleans_up_references_before_returning():
    signal = callbacks.Signal()
    with mock.patch.object(signal, '_cleanup_dead_refs') as cleanup_refs:
        signal._get_active_slots()
        cleanup_refs.assert_called_once()


def test_signal_is_empty_cleans_up_references_before_returning():
    signal = callbacks.Signal()
    with mock.patch.object(signal, '_cleanup_dead_refs') as cleanup_refs:
        assert signal.is_empty is True
        cleanup_refs.assert_called_once()


def test_signal_validate_slot_signature_returns_none_for_compat_args():
    signal = callbacks.Signal(int)
    def callback(x: int):
        del x  # Unused.
    signal._validate_slot_signature(callback)


def test_signal_validate_slot_signature_returns_none_for_named_args():
    signal = callbacks.Signal('SomeClass')
    class SomeClass:
        """Mock class."""
    def callback(cls: SomeClass):
        del cls  # Unused.
    signal._validate_slot_signature(callback)


def test_signal_validate_slot_signature_raises_type_error_for_too_few_args():
    signal = callbacks.Signal(int)
    def callback():
        pass
    with pytest.raises(TypeError):
        signal._validate_slot_signature(callback)


def test_signal_validate_slot_signature_raises_type_error_for_too_many_args():
    signal = callbacks.Signal(int)
    def callback(x: int, y: int):
        del x, y  # Unused.
    with pytest.raises(TypeError):
        signal._validate_slot_signature(callback)


def test_signal_validate_slot_signature_raises_type_error_for_incompat_args():
    signal = callbacks.Signal(int)
    def callback(name: str):
        del name  # Unused.
    with pytest.raises(TypeError):
        signal._validate_slot_signature(callback)


def test_signal_connection_adds_to_slot_refs():
    signal = callbacks.Signal()
    def callback():
        pass
    signal.connect(callback)
    assert signal.is_empty is False
    assert callback in signal._get_active_slots()


def test_signal_connection_allows_lambda_functions():
    signal = callbacks.Signal()
    callback = lambda: None
    signal.connect(callback)
    assert signal.is_empty is False
    assert callback in signal._get_active_slots()


def test_signal_connection_does_not_keep_dynamic_lambdas_in_memory():
    signal = callbacks.Signal()
    signal.connect(lambda: None)
    assert signal.is_empty is True


def test_signal_disconnection_by_callback_does_not_clear_all_slots():
    signal = callbacks.Signal()
    callback_a = lambda: None
    callback_b = lambda: None
    signal.connect(callback_a)
    signal.connect(callback_b)
    assert len(signal._get_active_slots()) == 2
    signal.disconnect(callback_a)
    assert len(signal._get_active_slots()) == 1


def test_signal_disconnect_without_callback_clears_all_slots():
    signal = callbacks.Signal()
    callback_a = lambda: None
    callback_b = lambda: None
    signal.connect(callback_a)
    signal.connect(callback_b)
    assert len(signal._get_active_slots()) == 2
    signal.disconnect()
    assert len(signal._get_active_slots()) == 0


@pytest.mark.asyncio
async def test_signal_emit_gathers_all_function_tasks():
    signal = callbacks.Signal()

    count = 0
    async def callback_1():
        nonlocal count
        count += 1

    async def callback_2():
        nonlocal count
        count += 1

    async def callback_3():
        nonlocal count
        count += 1

    signal.connect(callback_1, callback_2, callback_3)
    with asyncmock.patch.object(asyncio,
                                'gather',
                                side_effect=asyncio.gather) as mock_gather:
        await signal.emit()
        mock_gather.assert_called_once()
        assert count == 3


def test_slot_decorator_marks_function():
    @callbacks.slot
    def func():
        pass
    isinstance(func, callbacks.Slot)
