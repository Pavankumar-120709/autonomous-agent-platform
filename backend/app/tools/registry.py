from typing import Dict, List, Optional
from .base import BaseTool
from .web_search import WebSearchTool
from .webpage_reader import WebpageReaderTool
from .calculator import CalculatorTool
from .structured_notes import StructuredNotesTool


class ToolRegistry:
    def __init__(self, run_id: Optional[str] = None):
        self._tools: Dict[str, BaseTool] = {}
        self.run_id = run_id or "default"
        self._register_default_tools()

    def _register_default_tools(self):
        self.register(WebSearchTool())
        self.register(WebpageReaderTool())
        self.register(CalculatorTool())
        self.register(StructuredNotesTool(run_id=self.run_id))

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_openai_schemas(self) -> List[dict]:
        return [tool.get_openai_tool_schema() for tool in self._tools.values()]


def create_tool_registry(run_id: str) -> ToolRegistry:
    return ToolRegistry(run_id=run_id)
