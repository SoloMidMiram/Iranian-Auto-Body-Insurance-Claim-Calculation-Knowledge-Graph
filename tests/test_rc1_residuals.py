"""RC-1 engineering controls using immutable, explicitly synthetic inputs."""
import json
from pathlib import Path

import pytest

from iran_auto_claim.admission import _internal_test_direct_authorize
from iran_auto_claim.engine import compute
from iran_auto_claim.review import Review

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = ROOT / 'docs/reconciliation-evidence/synthetic-v1'


def case(name):
    return json.loads((SYNTHETIC / ('inspection-' + name + '.json')).read_text(encoding='utf-8'))


def test_c35_itemised_battery_binds_new_price_and_interaction(kb):
    review = Review(case('c35q404-battery-new-price'), kb)
    assert review.slot_status('PS_PART_NEW_PRICE').status == 'RESOLVED'
    assert review.slot_status('PS_BATTERY_TIRE_INTERACTION').status == 'RESOLVED'
    result = review.calculate()
    assert result is not None
    assert result.payable is None


def test_c48_selected_assessor_route_cannot_fall_back_to_year(kb):
    review = Review(case('c48-assessed-depreciation-figure'), kb)
    assert review.slot_status('PS_ASSESSED_DEPRECIATION').status == 'UNANSWERED'
    assert review.decision()['decision'] == 'INSUFFICIENT_INFORMATION'
    assert review.calculate() is None
    raw = review.case_payload()
    assert raw['damage']['depreciation_method'] == 'ASSESSED_FIGURE'
    result = compute(_internal_test_direct_authorize(raw, purpose='RC1_ASSESSOR_NEGATIVE'), kb)
    assert result.payable is None
    assert result.status == 'ASSESSED_DEPRECIATION_AMOUNT_REQUIRED'


@pytest.mark.parametrize('name,condition', [
    ('c97-late-notice-no-excuse', 'NOTICE_ADJUDICATION_REQUIRED'),
    ('c98-recourse-released', 'SUBROGATION_ADJUDICATION_REQUIRED'),
])
def test_unadjudicated_notice_and_recovery_block_review_not_zero(kb, name, condition):
    review = Review(case(name), kb)
    assert review.refusal_reasons() == []
    assert review.decision()['decision'] == 'INSUFFICIENT_INFORMATION'
    assert condition in review.decision()['blocking_conditions']
    assert review.calculate() is None


@pytest.mark.parametrize('name,status', [
    ('c97-late-notice-no-excuse', 'NOTICE_ADJUDICATION_REQUIRED'),
    ('c98-recourse-released', 'SUBROGATION_ADJUDICATION_REQUIRED'),
])
def test_unadjudicated_notice_and_recovery_block_direct_not_zero(kb, name, status):
    raw = Review(case(name), kb).case_payload()
    result = compute(_internal_test_direct_authorize(raw, purpose='RC1_ADJUDICATION_NEGATIVE'), kb)
    assert result.payable is None
    assert result.status == status


def test_on_time_no_impaired_recovery_control_still_computes(kb):
    payload = json.loads((ROOT / 'cases/review_t1_fullcover_partial.json').read_text(encoding='utf-8'))
    result = Review(payload, kb).calculate()
    assert result is not None
    assert result.payable == 1657000000
