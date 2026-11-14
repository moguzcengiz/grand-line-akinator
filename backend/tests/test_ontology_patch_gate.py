import pytest

from app import config
from app.ontology_patch_gate import validate_campaign_patch

# the gate reads the campaign's research records, which live in the git-ignored work/ directory
pytestmark = pytest.mark.skipif(not (config.ROOT / "work/research").exists(), reason="work/research not present")


def test_existing_campaign_patch_passes_lightweight_provenance_gate():
    result = validate_campaign_patch("054")
    assert result["failures"] == []
    assert result["warnings"] == []
    assert result["provenance_complete_assertions"] == result["new_assertions"]
    assert result["temporal_assertions"] == 6
