"""Tests the mason framework library system."""
# pylint: disable=protected-access, missing-function-docstring, redefined-outer-name

import os
import mock
import pytest

from mason import nodes
from mason import library


@pytest.fixture
def default_modules():
    _, _, filenames = next(os.walk(os.path.dirname(nodes.__file__)))
    return [f.split('.')[0]
            for f in filenames if f.endswith('.py') and f != '__init__.py']


def test_library_initialization_does_not_load_anything():
    with mock.patch.object(library.Library, 'load_defaults') as mock_load:
        lib = library.Library()
    assert len(lib.blueprint_types) == 0
    assert len(lib.node_types) == 0
    mock_load.assert_not_called()


def test_library_initialization_with_defaults_loads_mason_libs():
    with mock.patch.object(library.Library, 'load_defaults') as mock_load:
        lib = library.Library(autoload_defaults=True)
    assert len(lib.blueprint_types) == 0
    assert len(lib.node_types) == 0
    mock_load.assert_called_once()


def test_library_load_defaults_loads_mason_libs(default_modules):
    with mock.patch.object(library.Library, 'load') as mock_load:
        library.Library(autoload_defaults=True)

    for module in default_modules:
        mock_load.assert_any_call(f'mason.nodes.{module}')
    assert mock_load.call_count == len(default_modules)


def test_library_get_default_caches():
    library.get_default_library.cache_clear()
    try:
        with mock.patch.object(library,
                               'Library',
                               side_effect=library.Library) as mock_lib:
            default_a = library.get_default_library()
            default_b = library.get_default_library()
            default_c = library.get_default_library()

        assert default_a is default_b is default_c
        mock_lib.assert_called_once_with(autoload_defaults=True)
    finally:
        library.get_default_library.cache_clear()
