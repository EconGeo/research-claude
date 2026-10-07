import pytest
from data_tag.vocab import Vocab, slugify

@pytest.fixture(scope="module")
def vocab():
    return Vocab.load()

def test_loads_seed(vocab):
    assert vocab.version >= 1
    assert "costar" in vocab.sources and "hmda" in vocab.sources
    assert "residential-transactions-mls" in vocab.types
    assert "metro" in vocab.geo_levels and "house-price" in vocab.dv_classes

def test_match_costar_word_bounded(vocab):
    hits = vocab.match_sources("We obtain rents from CoStar for 2010–2019.")
    assert [h.slug for h in hits] == ["costar"]
    assert vocab.match_sources("Costs are higher; the costar analysis is irrelevant.") == []

def test_match_hmda_long_alias(vocab):
    hits = vocab.match_sources("Home Mortgage Disclosure Act data cover all lenders.")
    assert hits and hits[0].slug == "hmda"

def test_resolve_source_by_name_and_alias(vocab):
    assert vocab.resolve_source("CoStar Group") == "costar"
    assert vocab.resolve_source("American Community Survey") == "acs"
    assert vocab.resolve_source("REcolorado MLS") == "mls"
    assert vocab.resolve_source("Some Unknown Provider") is None

def test_resolve_dv(vocab):
    assert vocab.resolve_dv("log sale price") == "house-price"
    assert vocab.resolve_dv("monthly asking rent") == "rent"
    assert vocab.resolve_dv("tenure choice") is None

def test_slugify():
    assert slugify("Loan-Denial  Rate (HMDA)") == "loan-denial-rate-hmda"
