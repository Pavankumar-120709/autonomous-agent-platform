from abc import ABC, abstractmethod
import asyncio
import logging
import time
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field

logger = logging.getLogger("agent.tools")


class ToolExecutionMetadata(BaseModel):
    tool_name: str
    execution_time_ms: float
    timestamp: float
    retries: int = 0
    timeout_seconds: float
    input_size_bytes: int = 0
    output_size_bytes: int = 0


class ToolResult(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_summary(self, max_length: int = 500) -> str:
        if not self.success:
            return f"Error: {self.error}"
        text = str(self.data)
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text


class BaseTool(ABC):
    name: str
    description: str
    args_schema: Type[BaseModel]
    timeout_seconds: float = 15.0

    def __init__(self, timeout_seconds: Optional[float] = None):
        if timeout_seconds is not None:
            self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger(f"agent.tools.{self.name}")

    @abstractmethod
    async def _run(self, **kwargs) -> Any:
        """Core implementation of tool logic."""
        pass

    async def execute(self, **kwargs) -> ToolResult:
        """
        Executes the tool with strict validation, timeout bounding,
        error handling, and timing telemetry.
        """
        start_time = time.perf_counter()
        tool_log = self.logger

        input_str = str(kwargs)
        input_size = len(input_str.encode("utf-8"))

        tool_log.info(f"Executing tool '{self.name}' with input: {input_str[:200]}...")

        try:
            # Validate inputs against schema
            validated_args = self.args_schema(**kwargs)
            call_kwargs = validated_args.model_dump()

            # Execute with timeout
            data = await asyncio.wait_for(
                self._run(**call_kwargs),
                timeout=self.timeout_seconds
            )

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            output_str = str(data)
            output_size = len(output_str.encode("utf-8"))

            tool_log.info(f"Tool '{self.name}' succeeded in {duration_ms:.2f}ms")

            return ToolResult(
                success=True,
                data=data,
                error=None,
                execution_time_ms=round(duration_ms, 2),
                metadata={
                    "tool_name": self.name,
                    "execution_time_ms": round(duration_ms, 2),
                    "timestamp": time.time(),
                    "timeout_seconds": self.timeout_seconds,
                    "input_size_bytes": input_size,
                    "output_size_bytes": output_size,
                }
            )

        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            err_msg = f"Tool '{self.name}' timed out after {self.timeout_seconds} seconds."
            tool_log.error(err_msg)
            return ToolResult(
                success=False,
                data=None,
                error=err_msg,
                execution_time_ms=round(duration_ms, 2),
                metadata={
                    "tool_name": self.name,
                    "execution_time_ms": round(duration_ms, 2),
                    "timestamp": time.time(),
                    "timeout_seconds": self.timeout_seconds,
                    "timeout_occurred": True,
                }
            )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            err_msg = f"Tool execution failed: {type(exc).__name__}: {str(exc)}"
            tool_log.error(err_msg, exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                error=err_msg,
                execution_time_ms=round(duration_ms, 2),
                metadata={
                    "tool_name": self.name,
                    "execution_time_ms": round(duration_ms, 2),
                    "timestamp": time.time(),
                    "timeout_seconds": self.timeout_seconds,
                    "exception_class": type(exc).__name__,
                }
            )

    def get_openai_tool_schema(self) -> Dict[str, Any]:
        """Returns the OpenAPI / OpenAI compatible function definition schema."""
        schema = self.args_schema.model_json_schema()
        # Clean up unwanted metadata from json schema for OpenAI compatibility
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            }
        }
