import logging
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator
from .base import BaseTool

logger = logging.getLogger("agent.tools.structured_notes")


class NoteEntry(BaseModel):
    key: str
    content: str
    category: str = "general"
    sources: List[str] = Field(default_factory=list)
    updated_at: float


class StructuredNotesInput(BaseModel):
    action: Literal["save", "get", "list", "delete"] = Field(
        ...,
        description="Action to perform: 'save' a finding, 'get' a specific note by key, 'list' all notes, or 'delete' a note."
    )
    key: Optional[str] = Field(
        default=None,
        description="Unique identifier/title for the note (required for 'save', 'get', 'delete')."
    )
    content: Optional[str] = Field(
        default=None,
        description="The note findings/content to save (required for 'save')."
    )
    category: Optional[str] = Field(
        default="general",
        description="Category classification for the note (e.g. 'facts', 'metrics', 'sources', 'quotes')."
    )
    sources: Optional[List[str]] = Field(
        default_factory=list,
        description="List of URLs or reference names where this information was obtained."
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Agent run ID for session isolation."
    )

    @field_validator("key")
    def validate_key(cls, v: Optional[str], info) -> Optional[str]:
        action = info.data.get("action")
        if action in ("save", "get", "delete") and (not v or not v.strip()):
            raise ValueError(f"Key is required for action '{action}'")
        return v.strip().lower() if v else None


class StructuredNotesResult(BaseModel):
    action: str
    status: str
    message: str
    note: Optional[NoteEntry] = None
    all_notes: Optional[List[NoteEntry]] = None
    total_notes: int = 0


# Shared notes storage indexed by run_id
_NOTES_STORE: Dict[str, Dict[str, NoteEntry]] = {}


def get_run_notes(run_id: str) -> Dict[str, NoteEntry]:
    if run_id not in _NOTES_STORE:
        _NOTES_STORE[run_id] = {}
    return _NOTES_STORE[run_id]


def clear_run_notes(run_id: str) -> None:
    _NOTES_STORE.pop(run_id, None)


class StructuredNotesTool(BaseTool):
    name = "structured_notes"
    description = (
        "Save, retrieve, list, or delete structured research findings and notes during an agent run. "
        "Allows the agent to organize thoughts, store intermediate data, track sources, and retrieve prior observations."
    )
    args_schema = StructuredNotesInput
    timeout_seconds = 5.0

    def __init__(self, run_id: str = "global", timeout_seconds: Optional[float] = None):
        super().__init__(timeout_seconds=timeout_seconds)
        self.default_run_id = run_id

    async def _run(
        self,
        action: str,
        key: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = "general",
        sources: Optional[List[str]] = None,
        run_id: Optional[str] = None,
    ) -> StructuredNotesResult:
        import time

        active_run_id = run_id or self.default_run_id
        store = get_run_notes(active_run_id)

        if action == "save":
            if not content or not content.strip():
                raise ValueError("Content cannot be empty when saving a note.")

            entry = NoteEntry(
                key=key,
                content=content.strip(),
                category=category or "general",
                sources=sources or [],
                updated_at=time.time(),
            )
            store[key] = entry
            return StructuredNotesResult(
                action="save",
                status="saved",
                message=f"Note '{key}' successfully saved under category '{category}'.",
                note=entry,
                total_notes=len(store),
            )

        elif action == "get":
            if key not in store:
                return StructuredNotesResult(
                    action="get",
                    status="not_found",
                    message=f"Note with key '{key}' was not found.",
                    total_notes=len(store),
                )
            return StructuredNotesResult(
                action="get",
                status="found",
                message=f"Retrieved note '{key}'.",
                note=store[key],
                total_notes=len(store),
            )

        elif action == "list":
            notes_list = list(store.values())
            return StructuredNotesResult(
                action="list",
                status="success",
                message=f"Found {len(notes_list)} note(s).",
                all_notes=notes_list,
                total_notes=len(notes_list),
            )

        elif action == "delete":
            if key in store:
                deleted = store.pop(key)
                return StructuredNotesResult(
                    action="delete",
                    status="deleted",
                    message=f"Note '{key}' was successfully deleted.",
                    note=deleted,
                    total_notes=len(store),
                )
            return StructuredNotesResult(
                action="delete",
                status="not_found",
                message=f"Cannot delete: note '{key}' was not found.",
                total_notes=len(store),
            )

        else:
            raise ValueError(f"Unknown notes action '{action}'")
