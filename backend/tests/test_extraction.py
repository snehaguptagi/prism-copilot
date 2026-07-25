"""
Tests for extract_citations_and_narrative — parses the Anthropic response's
content blocks. Uses lightweight fakes matching the real SDK's attribute
shape (block.type, block.name, block.input, block.citations, block.text,
citation.url/title/cited_text) so no live API call is needed.
"""

from types import SimpleNamespace

from insight_lens import extract_citations_and_narrative


def _search_block(query):
    return SimpleNamespace(type="server_tool_use", name="web_search", input={"query": query})


def _citation(url, title="", cited_text="", ctype="web_search_result_location"):
    return SimpleNamespace(type=ctype, url=url, title=title, cited_text=cited_text)


def _text_block(text, citations=None):
    return SimpleNamespace(type="text", text=text, citations=citations)


def test_extracts_search_queries():
    response = SimpleNamespace(content=[_search_block("Reliance Industries news"), _text_block("hello")])
    result = extract_citations_and_narrative(response)
    assert result["queries_used"] == ["Reliance Industries news"]


def test_concatenates_narrative_text_blocks_in_order():
    response = SimpleNamespace(content=[_text_block("First part. "), _text_block("Second part.")])
    result = extract_citations_and_narrative(response)
    assert result["narrative"] == "First part. Second part."


def test_extracts_citations_from_text_blocks():
    citation = _citation("https://example.com/a", title="A", cited_text="fact A")
    response = SimpleNamespace(content=[_text_block("some text", citations=[citation])])
    result = extract_citations_and_narrative(response)
    assert result["citations"] == [{"url": "https://example.com/a", "title": "A", "cited_text": "fact A"}]


def test_dedupes_citations_by_url():
    c1 = _citation("https://example.com/a", title="A", cited_text="fact A v1")
    c2 = _citation("https://example.com/a", title="A", cited_text="fact A v2")
    response = SimpleNamespace(content=[
        _text_block("part 1", citations=[c1]),
        _text_block("part 2", citations=[c2]),
    ])
    result = extract_citations_and_narrative(response)
    assert len(result["citations"]) == 1


def test_ignores_citations_with_wrong_type():
    citation = _citation("https://example.com/a", ctype="something_else")
    response = SimpleNamespace(content=[_text_block("text", citations=[citation])])
    result = extract_citations_and_narrative(response)
    assert result["citations"] == []


def test_handles_text_block_with_no_citations_attribute():
    response = SimpleNamespace(content=[_text_block("plain text with no citations field")])
    result = extract_citations_and_narrative(response)
    assert result["narrative"] == "plain text with no citations field"
    assert result["citations"] == []


def test_empty_content_returns_empty_everything():
    response = SimpleNamespace(content=[])
    result = extract_citations_and_narrative(response)
    assert result == {"queries_used": [], "citations": [], "narrative": ""}
