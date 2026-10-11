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
    assert vocab.resolve_dv("tenure choice") == "homeownership-tenure"  # v4: was None before the tenure class

def test_slugify():
    assert slugify("Loan-Denial  Rate (HMDA)") == "loan-denial-rate-hmda"

def test_match_assessor_curly_apostrophe(vocab):
    hits = vocab.match_sources("Data from county assessor’s records.")
    assert hits and hits[0].slug == "assessor"

def test_match_moodys_curly_apostrophe(vocab):
    hits = vocab.match_sources("Moody’s CRE data.")
    assert hits and hits[0].slug == "moodys_cre"

def test_resolve_dv_word_boundary(vocab):
    # Should not match "apparent" as a word start for rent
    assert vocab.resolve_dv("apparent effect") is None
    # Should not match "random" as a word start for time-on-market
    assert vocab.resolve_dv("random effects") is None
    # "price-to-income" matches affordability (longer needle "rent-to-income" not in text)
    assert vocab.resolve_dv("price-to-income ratio") == "affordability"
    # Should match "rent-to-income" needle
    assert vocab.resolve_dv("rent-to-income") == "affordability"


@pytest.mark.parametrize("name,dv", [
    ("days-on-market", "time-on-market"), ("days_on_market", "time-on-market"), ("TOM", "time-on-market"),
    ("log DOM", "time-on-market"), ("domestic migration", None), ("tomorrow", None),
    ("Case-Shiller HPI", "house-price"), ("chip", None), ("sale/price", "house-price"),
    ("rent  to  income", "affordability")])
def test_resolve_dv_normalised_and_caps_needles(vocab, name, dv):
    assert vocab.resolve_dv(name) == dv


def test_resolve_dv_dividend_yield_known_limit(vocab):
    # 'yield' is a plan-vocabulary cap-rate needle; "dividend yield" still lands there (known, accepted).
    assert vocab.resolve_dv("dividend yield") == "cap-rate"


def test_psh_alias_removed(vocab):
    assert vocab.match_sources("permanent supportive housing (PSH) units") == []
    assert [h.slug for h in vocab.match_sources("HUD Picture of Subsidized Households")] == ["hud_posh"]


def test_v3_sources(vocab):
    assert vocab.version >= 3
    assert vocab.resolve_source("CHAS data") == "hud_chas"
    assert vocab.resolve_source("Census PUMS data") == "pums"
    assert vocab.resolve_source("REALIS database") == "realis"


@pytest.mark.parametrize("name,dv", [
    ("HHI (Herfindahl-Hirschman Index)", "market-concentration"),
    ("largest firm's market share", "market-concentration"),
    ("HCV subsidies", "subsidy-voucher"),
    ("number of sold houses", "transaction-volume"),
    ("SP", "house-price"), ("S&P 500 return", None), ("spatial", None)])
def test_v3_dv_classes(vocab, name, dv):
    assert vocab.resolve_dv(name) == dv


@pytest.mark.parametrize("name,slug", [
    ("FHFA house price index", "fhfa_hpi"), ("Case\u2013Shiller\u2013Weiss repeat sales indexes (CSW)", "case_shiller"),
    ("IPUMS USA", "ipums"), ("Housing Vacancy Survey", "hvs"),
    ("Bureau of Economic Analysis per capita income", "bea"), ("NAR transactions", "nar"),
    ("Warren Group data", "warren_group"), ("Survey of English Housing", "seh"),
    ("Family Resources Survey (FRS)", "frs"), ("Census Bureau population", "census"),
    ("Zillow.com data on price appreciation", "zillow")])
def test_v4_sources(vocab, name, slug):
    assert vocab.version >= 4
    assert vocab.resolve_source(name) == slug


@pytest.mark.parametrize("name,dv", [
    ("Serious payment problem", "default-foreclosure"), ("apartment renewal rates", "rent"),
    ("annual household growth", "household-formation"),
    ("down payment (wealth) constraint", "homeownership-tenure"),
    ("household consumption", "consumption")])
def test_v4_dv_classes(vocab, name, dv):
    assert vocab.resolve_dv(name) == dv


def test_v4_aliases_quiet_on_prose(vocab):
    prose = ("The bea ch was crowded; a nar row road and a fhfa... Their csw of tenure and the warren, "
             "a census taker, and the housing survey of nearby frs areas were noted.")
    assert vocab.match_sources(prose) == []


@pytest.mark.parametrize("name,slug", [
    ("Situs RERC property discount rates", "situs_rerc"),
    ("Survey of Professional Forecasters at the Federal Reserve", "spf"),
    ("Australian Property Monitors (APM)", "apm"),
    ("Australian Bureau of Statistics (ABS) Census", "abs_census"),
    ("S&P Global REIT rental revenues", "snl"),
    ("S&P CoreLogic Case-Shiller index", "case_shiller"),
    ("S&P 500 returns", None),
])
def test_v5_sources(vocab, name, slug):
    assert vocab.version == 5
    assert vocab.resolve_source(name) == slug


@pytest.mark.parametrize("name,dv", [
    ("MLS market penetration", "brokerage-market-share"),
    ("largest firm's market share", "market-concentration"),
])
def test_v5_dv_classes(vocab, name, dv):
    assert vocab.resolve_dv(name) == dv
