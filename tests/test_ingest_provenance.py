"""Provenance is the corpus's load-bearing property: "authoritative" must mean a
New Zealand regulator. These tests pin the classification rules that keep
manufacturer and advocacy material from being presented as regulator fact."""

from ingest import (AUTHORITY, normalise_stance, publisher_short,
                    strip_maintainer_notes)
from joulie.rag import Retriever

REL = "knowledge_base/Product Specs/evs/x.md"


class TestPublisherShort:
    def test_a_manufacturer_is_never_labelled_ea(self):
        # "EA" is the Electricity Authority. A bare substring test matched the
        # "ea" in "New Zealand" and tagged every local distributor as the
        # regulator; these are the exact publishers that broke.
        for publisher in ("BYD New Zealand", "Kia New Zealand", "Nissan New Zealand",
                          "Rinnai New Zealand", "Hyundai New Zealand"):
            meta = {"publisher": publisher, "brand": publisher.split()[0]}
            assert publisher_short(REL, meta) != "EA"

    def test_brand_wins_over_folder_and_publisher(self):
        meta = {"publisher": "Tesla, Inc.", "brand": "Tesla"}
        assert publisher_short(REL, meta) == "Tesla"

    def test_authority_field_maps_to_short_label(self):
        assert publisher_short(REL, {"authority": "MBIE"}) == "MBIE"
        assert publisher_short(REL, {"authority": "Electricity Authority"}) == "EA"

    def test_the_real_electricity_authority_still_resolves(self):
        assert publisher_short(REL, {"publisher": "Electricity Authority"}) == "EA"

    def test_topic_folder_is_not_mistaken_for_a_publisher(self):
        # "Policy Data" is a topic, not a publisher, unlike "MBIE Website".
        assert publisher_short("knowledge_base/Policy Data/mbie/x.md", {}) == "unknown"


class TestStance:
    def test_product_specs_are_vendor_not_authoritative(self):
        assert normalise_stance({"brand": "Tesla", "publisher": "Tesla, Inc."}) == "vendor"

    def test_regulators_stay_authoritative(self):
        assert normalise_stance({"authority": "EECA"}) == "authoritative"
        assert normalise_stance({"authority": "MBIE"}) == "authoritative"

    def test_industry_bodies_are_advocacy(self):
        assert normalise_stance({"authority": "BusinessNZ Energy Council"}) == "advocacy"

    def test_rewiring_is_still_advocacy(self):
        assert normalise_stance({"publisher": "Rewiring Aotearoa"}) == "advocacy"

    def test_unprovenanced_content_is_not_promoted(self):
        assert normalise_stance({}) == "reference"

    def test_every_authority_maps_to_a_known_stance(self):
        assert {s for _, s in AUTHORITY.values()} <= {"authoritative", "advocacy", "reference"}


class TestContextFraming:
    def test_vendor_material_is_labelled_as_manufacturer_claims(self):
        ctx = Retriever.format_context([
            {"text": "750 km WLTP range.", "stance": "vendor",
             "publisher_short": "Tesla", "title": "Model 3", "source_date": ""}])
        assert "Manufacturer specifications" in ctx
        assert "never as a recommendation" in ctx

    def test_vendor_material_is_not_filed_under_authoritative(self):
        ctx = Retriever.format_context([
            {"text": "750 km WLTP range.", "stance": "vendor",
             "publisher_short": "Tesla", "title": "Model 3", "source_date": ""}])
        assert "Authoritative sources" not in ctx

    def test_an_unknown_stance_falls_back_to_reference_not_authoritative(self):
        ctx = Retriever.format_context([
            {"text": "Something.", "stance": "typo-stance",
             "publisher_short": "X", "title": "T", "source_date": ""}])
        assert "Authoritative sources" not in ctx
        assert "Reference / signposting" in ctx


class TestLegacyCorpus:
    """The EECA Website corpus predates both stance fields: 76 files carry a
    publisher and nothing else, and relied on the old "authoritative" default.
    Tightening the default must not quietly demote them."""

    def test_legacy_eeca_files_stay_authoritative(self):
        meta = {"publisher": "EECA (Energy Efficiency & Conservation Authority), "
                             "New Zealand Government"}
        assert normalise_stance(meta) == "authoritative"
        assert publisher_short("knowledge_base/EECA Website/x.md", meta) == "EECA"

    def test_an_unrecognised_publisher_is_not_promoted(self):
        assert normalise_stance({"publisher": "Some Blog"}) == "reference"


class TestMaintainerNotes:
    """Every product-spec file ends with an aside addressed to whoever maintains
    the corpus. Embedded, they retrieve as if they were NZ energy facts."""

    def test_the_note_is_removed(self):
        body = ("# Tesla Model 3\n\nRange is 750 km WLTP.\n\n"
                "## Note for corpus maintainers\n\n"
                "*Reconcile against RightCar's official record.*\n")
        out = strip_maintainer_notes(body)
        assert "RightCar" not in out and "corpus maintainers" not in out

    def test_the_real_content_survives(self):
        body = ("# Tesla Model 3\n\nRange is 750 km WLTP.\n\n"
                "## Note for corpus maintainers\n\nEditorial aside.\n")
        assert "750 km WLTP" in strip_maintainer_notes(body)

    def test_a_following_section_of_the_same_level_survives(self):
        body = ("## Note for corpus maintainers\n\nAside.\n\n"
                "## Charging\n\nCCS2 up to 250 kW.\n")
        out = strip_maintainer_notes(body)
        assert "Aside." not in out
        assert "CCS2 up to 250 kW." in out

    def test_a_body_without_a_note_is_unchanged(self):
        body = "# Heat pumps\n\nA heat pump moves heat."
        assert strip_maintainer_notes(body) == body
