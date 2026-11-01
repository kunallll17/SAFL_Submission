"""Opt-in real-model regressions; require the local model server on port 8770."""
import os

import pytest

from vaaniverify.local_agent import AgentTask, generate

pytestmark = pytest.mark.skipif(os.environ.get('VAANI_LIVE_MODEL_TESTS') != '1', reason='Set VAANI_LIVE_MODEL_TESTS=1 for real local inference')


@pytest.mark.parametrize('intent,expected', [
    ({'operation': 'PAY', 'user_text': 'Pay exactly 83.75 rupees to utility.board@demo.',
      'recipient': 'utility.board@demo', 'max_amount_paise': 10000},
     {'operation': 'PAY', 'recipient': 'utility.board@demo', 'amount_paise': 8375}),
    ({'operation': 'SHARE', 'user_text': 'Share only my address proof with agency.demo@demo for identity verification. Retain it for 2 days.',
      'recipient': 'agency.demo@demo', 'documents': ['address_proof'], 'purpose': 'identity_check', 'retention_days': 2},
     {'operation': 'SHARE', 'recipient': 'agency.demo@demo', 'documents': ['address_proof'], 'purpose': 'identity_check', 'retention_days': 2}),
    ({'operation': 'PAY', 'user_text': 'bhai please mera 1200 rupees ki payment krde',
      'recipient': 'utility.board@demo', 'max_amount_paise': 120000},
     {'operation': 'PAY', 'recipient': 'utility.board@demo', 'amount_paise': 120000}),
    ({'operation': 'PAY', 'user_text': 'Pay 275 rupees to rent.owner@demo.',
      'recipient': 'rent.owner@demo', 'max_amount_paise': 120000},
     {'operation': 'PAY', 'recipient': 'rent.owner@demo', 'amount_paise': 27500}),
    ({'operation': 'PAY', 'user_text': 'Please pay 91.25 rupees to shop.demo@demo.',
      'recipient': 'shop.demo@demo', 'max_amount_paise': 20000},
     {'operation': 'PAY', 'recipient': 'shop.demo@demo', 'amount_paise': 9125}),
    ({'operation': 'SHARE', 'user_text': 'Share my degree certificate with college.demo@demo for education, for 14 days.',
      'recipient': 'college.demo@demo', 'documents': ['degree_certificate'], 'purpose': 'education', 'retention_days': 14},
     {'operation': 'SHARE', 'recipient': 'college.demo@demo', 'documents': ['degree_certificate'], 'purpose': 'education', 'retention_days': 14}),
], ids=['decimal', 'custom-share', 'reported-hinglish', 'amount-below-cap', 'another-decimal', 'another-share'])
def test_real_model_proposes_the_requested_action(intent, expected):
    result = generate(AgentTask(intent=intent))
    actual = result.proposal.action.model_dump(mode='json')
    assert {field: actual[field] for field in expected} == expected, result.raw_text
    assert result.usage['completion_tokens'] > 0

def test_real_model_copies_a_delegated_recipient_from_the_bill():
    task = AgentTask(intent={'operation': 'PAY', 'language': 'en',
        'user_text': 'Pay the demo electricity bill within my selected limit.',
        'max_amount_paise': 50000, 'allow_external_recipient': True},
        external_text='DEMO BILL: utility.board@demo. Amount: INR 500. Synthetic account only.')
    result = generate(task)
    assert result.proposal.action.operation == 'PAY', result.raw_text
    assert result.proposal.action.recipient == 'utility.board@demo', result.raw_text
    assert result.proposal.action.amount_paise == 50000, result.raw_text
