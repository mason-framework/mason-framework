"""Define Pythagorean tests."""

import pytest

import mason


@pytest.mark.asyncio
async def test_pythagorean_via_yaml():
    bp = mason.load_blueprint('examples/pythagorean.yaml')
    actual = await bp(a=3, b=4)
    assert actual == 5


@pytest.mark.asyncio
async def test_pythagorean_via_json():
    bp = mason.load_blueprint('examples/pythagorean.json')
    actual = await bp(a=3, b=4)
    assert actual == 5


@pytest.mark.asyncio
async def test_pythagorean_via_code():
    bp = mason.Blueprint()
    bp.create('flow.Input', name='a')
    bp.create('flow.Input', name='b')
    bp.create('math.Pow', name='a2', values={'base': bp['a.value']})
    bp.create('math.Pow', name='b2', values={'base': bp['b.value']})
    bp.create('math.Add', name='add', values={'a': bp['a2.value'],
                                              'b': bp['b2.value']})
    bp.create('math.Sqrt', name='sqrt', values={'number': bp['add.value']})
    bp.create('flow.Return', name='c', values={'value': bp['sqrt.value']})
    bp.connect('triggered', 'c.return_')
    actual = await bp(a=3, b=4)
    assert actual == 5
