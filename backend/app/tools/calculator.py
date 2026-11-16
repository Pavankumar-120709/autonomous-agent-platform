import ast
import math
import operator
from typing import Any, Dict, Union
from pydantic import BaseModel, Field, field_validator
from .base import BaseTool


SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_FUNCTIONS: Dict[str, Any] = {
    "sqrt": math.sqrt,
    "cbrt": lambda x: math.pow(x, 1/3) if x >= 0 else -math.pow(-x, 1/3),
    "pow": math.pow,
    "abs": abs,
    "round": round,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
}

SAFE_CONSTANTS: Dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}

MAX_EXPRESSION_LENGTH = 500
MAX_EXPONENT = 1000.0
MAX_FACTORIAL_ARG = 100


class CalculatorInput(BaseModel):
    expression: str = Field(
        ...,
        description="The mathematical expression to evaluate, e.g. '(15 * 4.2) + sqrt(144)' or 'log10(1000)'."
    )

    @field_validator("expression")
    def validate_expression(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Expression cannot be empty")
        if len(clean) > MAX_EXPRESSION_LENGTH:
            raise ValueError(f"Expression exceeds maximum length of {MAX_EXPRESSION_LENGTH} characters")
        return clean


class CalculatorResult(BaseModel):
    expression: str
    result: Union[int, float]
    formatted: str


class SafeEvaluator(ast.NodeVisitor):
    def __init__(self):
        self.node_count = 0
        self.max_nodes = 200

    def visit(self, node):
        self.node_count += 1
        if self.node_count > self.max_nodes:
            raise ValueError("Expression complexity exceeded limit.")
        return super().visit(node)

    def visit_Expression(self, node: ast.Expression):
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    def visit_Name(self, node: ast.Name):
        name = node.id
        if name in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[name]
        if name in SAFE_FUNCTIONS:
            return SAFE_FUNCTIONS[name]
        raise ValueError(f"Variable or function '{name}' is not allowed or defined.")

    def visit_UnaryOp(self, node: ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unary operator '{op_type.__name__}' is not permitted.")
        operand = self.visit(node.operand)
        return SAFE_OPERATORS[op_type](operand)

    def visit_BinOp(self, node: ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Binary operator '{op_type.__name__}' is not permitted.")

        left = self.visit(node.left)
        right = self.visit(node.right)

        # Safety bounds for exponentiation
        if op_type == ast.Pow:
            if abs(right) > MAX_EXPONENT:
                raise ValueError(f"Exponent exceeds safe limit ({MAX_EXPONENT}).")
            if abs(left) > 1000 and right > 10:
                raise ValueError("Calculation would overflow numerical limits.")

        if op_type in (ast.Div, ast.FloorDiv, ast.Mod):
            if right == 0:
                raise ZeroDivisionError("Division by zero is undefined.")

        return SAFE_OPERATORS[op_type](left, right)

    def visit_Call(self, node: ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Complex function invocations are not permitted.")

        func_name = node.func.id
        if func_name not in SAFE_FUNCTIONS:
            raise ValueError(f"Function '{func_name}' is not permitted.")

        func = SAFE_FUNCTIONS[func_name]
        args = [self.visit(arg) for arg in node.args]

        if func_name == "factorial":
            if not args or not isinstance(args[0], int) or args[0] < 0:
                raise ValueError("Factorial requires a non-negative integer.")
            if args[0] > MAX_FACTORIAL_ARG:
                raise ValueError(f"Factorial argument exceeds safe limit ({MAX_FACTORIAL_ARG}).")

        try:
            return func(*args)
        except ZeroDivisionError:
            raise
        except ValueError as e:
            raise ValueError(f"Math domain error in {func_name}: {e}")
        except OverflowError:
            raise ValueError(f"Math overflow error evaluating {func_name}")

    def generic_visit(self, node):
        raise ValueError(f"Disallowed syntactic construct: {type(node).__name__}")


class CalculatorTool(BaseTool):
    name = "calculator"
    description = (
        "Safely evaluate mathematical and arithmetic expressions without arbitrary code execution. "
        "Supports operations (+, -, *, /, //, %, **), constants (pi, e, tau), and functions "
        "(sqrt, cbrt, pow, abs, round, sin, cos, tan, log, log2, log10, exp, ceil, floor, factorial)."
    )
    args_schema = CalculatorInput
    timeout_seconds = 5.0

    async def _run(self, expression: str) -> CalculatorResult:
        try:
            parsed = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Syntax error in mathematical expression: {e.msg} (offset: {e.offset})")

        evaluator = SafeEvaluator()
        raw_result = evaluator.visit(parsed)

        if isinstance(raw_result, (int, float)):
            # Normalize float representation if it's whole
            if isinstance(raw_result, float) and raw_result.is_integer() and abs(raw_result) < 1e15:
                res_val = int(raw_result)
            else:
                res_val = round(raw_result, 8) if isinstance(raw_result, float) else raw_result
        else:
            raise ValueError(f"Expression did not evaluate to a number (got {type(raw_result).__name__})")

        return CalculatorResult(
            expression=expression,
            result=res_val,
            formatted=f"{expression} = {res_val}"
        )
