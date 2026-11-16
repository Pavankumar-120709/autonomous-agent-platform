import pytest
from app.tools.structured_notes import StructuredNotesTool, clear_run_notes
from app.tools.web_search import WebSearchTool
from app.tools.webpage_reader import WebpageReaderTool
from app.tools.registry import create_tool_registry
from app.security.sanitizer import extract_and_sanitize_html, wrap_untrusted_content


@pytest.mark.asyncio
async def test_structured_notes_lifecycle():
    run_id = "test-run-123"
    clear_run_notes(run_id)
    notes = StructuredNotesTool(run_id=run_id)

    # 1. Save
    res1 = await notes.execute(
        action="save",
        key="findings_summary",
        content="AI reasoning demonstrates high accuracy.",
        category="metrics",
        sources=["https://example.com/paper"],
        run_id=run_id,
    )
    assert res1.success is True
    assert res1.data.status == "saved"
    assert res1.data.note.key == "findings_summary"

    # 2. Get
    res2 = await notes.execute(action="get", key="findings_summary", run_id=run_id)
    assert res2.success is True
    assert res2.data.status == "found"
    assert res2.data.note.content == "AI reasoning demonstrates high accuracy."

    # 3. List
    res3 = await notes.execute(action="list", run_id=run_id)
    assert res3.success is True
    assert res3.data.total_notes == 1

    # 4. Delete
    res4 = await notes.execute(action="delete", key="findings_summary", run_id=run_id)
    assert res4.success is True
    assert res4.data.status == "deleted"

    clear_run_notes(run_id)


def test_html_sanitizer_and_injection_wrapper():
    html = """
    <html>
      <head><title>Research Article</title></head>
      <body>
        <script>alert('pwned');</script>
        <style>body { color: red; }</style>
        <main>
          <h1>Quantum Superposition</h1>
          <p>Quantum superposition is a fundamental principle of quantum mechanics.</p>
        </main>
      </body>
    </html>
    """
    clean = extract_and_sanitize_html(html)
    assert "alert" not in clean
    assert "<script>" not in clean
    assert "Quantum Superposition" in clean
    assert "Title: Research Article" in clean

    wrapped = wrap_untrusted_content(clean, source="https://quantum.org")
    assert "BEGIN UNTRUSTED EXTERNAL WEBPAGE CONTENT" in wrapped
    assert "SECURITY NOTICE" in wrapped
    assert "END UNTRUSTED EXTERNAL WEBPAGE CONTENT" in wrapped


@pytest.mark.asyncio
async def test_web_search_validation():
    search = WebSearchTool()
    # Empty query rejection
    res = await search.execute(query="   ")
    assert res.success is False
    assert "cannot be empty" in res.error.lower()


def test_tool_registry():
    registry = create_tool_registry("test-run-456")
    tools = registry.list_tools()
    assert len(tools) == 4

    names = {t.name for t in tools}
    assert names == {"web_search", "webpage_reader", "calculator", "structured_notes"}

    schemas = registry.get_openai_schemas()
    assert len(schemas) == 4
    for s in schemas:
        assert s["type"] == "function"
        assert "name" in s["function"]
        assert "parameters" in s["function"]
