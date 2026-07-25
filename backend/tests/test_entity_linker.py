"""
Tests for link_citations_to_securities — the substring/word-boundary matcher.
Includes an explicit regression test for the real bug found in this project:
a short alias ("RIL") matching inside an unrelated English word ("primarily").
"""

from insight_lens import link_citations_to_securities

SECURITIES = [
    {"security_id": "sec_reliance", "primary_ticker": "RELIANCE", "name": "Reliance Industries Ltd",
     "aliases": ["Reliance", "RIL", "Reliance Industries"]},
    {"security_id": "sec_dixon", "primary_ticker": "DIXON", "name": "Dixon Technologies Ltd",
     "aliases": ["Dixon Technologies", "Dixon"]},
    {"security_id": "sec_hcltech", "primary_ticker": "HCLTECH", "name": "HCL Technologies Ltd",
     "aliases": ["HCL Technologies", "HCLTech", "HCL Tech"]},
    {"security_id": "sec_tcs", "primary_ticker": "TCS", "name": "Tata Consultancy Services Ltd",
     "aliases": ["TCS", "Tata Consultancy Services"]},
    {"security_id": "sec_cash_inr", "primary_ticker": "INRCASH", "name": "INR Cash & Equivalents",
     "aliases": ["Money Market Cash"]},
]


def _citation(title="", cited_text=""):
    return {"url": "https://example.com", "title": title, "cited_text": cited_text}


def test_regression_ril_does_not_match_inside_primarily():
    """The exact bug found in this project: 'RIL' is a substring of 'primarily'."""
    citations = [_citation(cited_text="The reduction will primarily affect middle management.")]
    linked = link_citations_to_securities(citations, SECURITIES)
    assert linked[0]["linked_security_ids"] == []


def test_exact_company_name_match():
    citations = [_citation(title="Reliance Industries posts record profit")]
    linked = link_citations_to_securities(citations, SECURITIES)
    assert linked[0]["linked_security_ids"] == ["sec_reliance"]


def test_ticker_match_is_case_insensitive():
    citations = [_citation(cited_text="reliance shares rallied today")]
    linked = link_citations_to_securities(citations, SECURITIES)
    assert linked[0]["linked_security_ids"] == ["sec_reliance"]


def test_alias_with_space_matches_as_whole_word():
    """Regression for the real HCL Tech gap: alias must match 'HCL Tech' as a
    phrase (with the space), not require the no-space 'HCLTech' form."""
    citations = [_citation(title="TCS, Infosys, HCL Tech, Wipro: brokers cut targets")]
    linked = link_citations_to_securities(citations, SECURITIES)
    assert "sec_hcltech" in linked[0]["linked_security_ids"]
    assert "sec_tcs" in linked[0]["linked_security_ids"]


def test_no_match_returns_empty_list_not_none():
    citations = [_citation(title="Global oil prices rose on supply concerns")]
    linked = link_citations_to_securities(citations, SECURITIES)
    assert linked[0]["linked_security_ids"] == []


def test_multiple_securities_in_one_citation():
    citations = [_citation(title="TCS and Dixon both rose in early trade")]
    linked = link_citations_to_securities(citations, SECURITIES)
    assert set(linked[0]["linked_security_ids"]) == {"sec_tcs", "sec_dixon"}


def test_short_aliases_are_ignored():
    """Needles of length <= 2 are skipped entirely to avoid noise (e.g. a
    ticker like 'LT' would otherwise match inside dozens of ordinary words)."""
    securities = [{"security_id": "sec_lt", "primary_ticker": "LT", "name": "Larsen & Toubro Ltd",
                   "aliases": ["L&T"]}]
    citations = [_citation(cited_text="lt is a common abbreviation with no relation to this company")]
    linked = link_citations_to_securities(citations, securities)
    assert linked[0]["linked_security_ids"] == []


def test_preserves_citation_fields():
    citations = [_citation(title="Reliance news", cited_text="some text")]
    linked = link_citations_to_securities(citations, SECURITIES)
    assert linked[0]["title"] == "Reliance news"
    assert linked[0]["url"] == "https://example.com"


def test_regression_cash_does_not_match_inside_cash_burn():
    """Real bug found via a live news-feed run: the generic word 'cash' (once
    an alias/ticker for the INR cash holding) matched inside 'cash burn' in an
    unrelated startup-funding article, falsely flagging clients who simply
    hold cash as 'touched' by news that had nothing to do with them."""
    citations = [_citation(cited_text="lower cash burn as the primary trigger for backing tech IPOs")]
    linked = link_citations_to_securities(citations, SECURITIES)
    assert linked[0]["linked_security_ids"] == []
