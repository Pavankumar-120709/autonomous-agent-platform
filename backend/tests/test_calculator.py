import pytest
from app.tools.calculator import CalculatorTool


@pytest.mark.asyncio
async def test_calculator_basic_operations():
    calc = CalculatorTool()
    res = await calc.execute(expression="2 + 3 * 4")
    assert res.success is True
    assert res.data.result == 14

    res2 = await calc.execute(expression="(100 - 25) / 5")
    assert res2.success is True
    assert res2.data.result == 15


@pytest.mark.asyncio
async def test_calculator_advanced_math_and_constants():
    calc = CalculatorTool()
    res = await calc.execute(expression="sqrt(144) + abs(-8)")
    assert res.success is True
    assert res.data.result == 20

    res_pi = await calc.execute(expression="round(pi, 4)")
    assert res_pi.success is True
    assert res_pi.data.result == 3.1416


@pytest.mark.asyncio
async def test_calculator_blocks_arbitrary_code_execution():
    calc = CalculatorTool()

    # Disallow __import__
    res1 = await calc.execute(expression="__import__('os').system('ls')")
    assert res1.success is False
    assert "not allowed or defined" in res1.error or "not permitted" in res1.error

    # Disallow system calls
    res2 = await calc.execute(expression="eval('2+2')")
    assert res2.success is False
    assert "not permitted" in res2.error or "not allowed" in res2.error

    # Disallow lambda / list comprehension
    res3 = await calc.execute(expression="[x for x in (1, 2, 3)]")
    assert res3.success is False
    assert "Disallowed" in res3.error or "error" in res3.error


@pytest.mark.asyncio
async def test_calculator_handles_zero_division_and_overflow():
    calc = CalculatorTool()
    res_div = await calc.execute(expression="42 / 0")
    assert res_div.success is False
    assert "Division by zero" in res_div.error

    res_pow = await calc.execute(expression="9999 ** 9999")
    assert res_pow.success is False
    assert "overflow" in res_pow.error.lower() or "exceeds" in res_pow.error.lower()
