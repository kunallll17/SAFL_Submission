"""Optional rendered regression tests. See docs/FUNCTIONAL_VERIFICATION.md for the command."""
import os
import secrets
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn

playwright = pytest.importorskip('playwright.sync_api', reason='Install Playwright to run rendered demo regressions')

from vaaniverify.gateway import Gateway
from vaaniverify.kernel import Kernel
from vaaniverify.local_agent import Generation, ModelProposal
from vaaniverify.server import create_app


@pytest.fixture
def demo_page(tmp_path, monkeypatch):
    import vaaniverify.server as server_module

    seen = []
    raw = '{"action":{"operation":"PAY","recipient":"utility.board@demo","amount_paise":120000},"agent_message":"A proposal only"}'

    def generate(task):
        seen.append(task)
        return Generation(ModelProposal.model_validate_json(raw), raw, 1234, 'browser-test-model', {'prompt_tokens': 120, 'completion_tokens': 42})

    monkeypatch.setattr(server_module, 'generate', generate)
    kernel = Kernel()
    gateway = Gateway(kernel.signing_key.public_key(), tmp_path / 'ledger.db')
    bootstrap = secrets.token_urlsafe(32)
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    origin = f'http://127.0.0.1:{sock.getsockname()[1]}'
    app = create_app(kernel, gateway, bootstrap, secrets.token_urlsafe(32), origin=origin, execution_transport=gateway.execute)
    server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.01)
        assert server.started
        with playwright.sync_playwright() as p:
            executable = os.environ.get('VAANI_BROWSER_EXECUTABLE', p.chromium.executable_path)
            if not Path(executable).is_file():
                pytest.skip('Set VAANI_BROWSER_EXECUTABLE or install Playwright Chromium')
            browser = p.chromium.launch(executable_path=executable, headless=True)
            context = browser.new_context(viewport={'width': 1280, 'height': 900})
            page = context.new_page()
            page.goto(origin + '/demo#bootstrap=' + bootstrap)
            playwright.expect(page.locator('#run-agent')).to_be_enabled()
            yield page, seen, gateway, raw
            context.close()
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()


def test_custom_request_does_not_send_the_previous_example_bill(demo_page):
    page, seen, gateway, _ = demo_page
    page.locator('#request').fill('bhai please mera 1200 rupees ki payment krde')
    page.locator('#amount').fill('1200')
    page.locator('#run-agent').click()
    playwright.expect(page.locator('#decision')).to_be_visible()
    assert seen[0].intent.user_text == 'bhai please mera 1200 rupees ki payment krde'
    assert seen[0].intent.max_amount_paise == 120000
    assert seen[0].external_text == ''
    assert not gateway.receipts()


@pytest.mark.parametrize('field,value', [('amount', '1200'), ('recipient', 'rent.owner@demo'), ('example', 'custom')])
def test_switching_away_from_an_example_discards_only_its_message(demo_page, field, value):
    page, _, _, _ = demo_page
    if field == 'example':
        page.locator('#example').select_option(value)
    else:
        page.locator('#' + field).fill(value)
    playwright.expect(page.locator('#external-message')).to_have_value('')


def test_custom_external_message_survives_task_and_limit_edits(demo_page):
    page, seen, _, _ = demo_page
    page.locator('#message-details').evaluate('(el) => { el.open = true; }')
    page.locator('#external-message').fill('My own invoice: INR 725 to utility.board@demo.')
    page.locator('#request').fill('Pay my invoice')
    page.locator('#amount').fill('1200')
    page.locator('#run-agent').click()
    playwright.expect(page.locator('#decision')).to_be_visible()
    assert seen[0].external_text == 'My own invoice: INR 725 to utility.board@demo.'


def test_attack_example_keeps_its_external_instructions(demo_page):
    page, seen, _, _ = demo_page
    page.locator('#example').select_option('payee-swap')
    page.locator('#run-agent').click()
    playwright.expect(page.locator('#decision')).to_be_visible()
    assert 'cashback.claim@demo' in seen[0].external_text
    assert seen[0].intent.recipient == 'utility.board@demo'


def test_review_exposes_actual_model_input_and_output(demo_page):
    page, _, _, raw = demo_page
    page.locator('#request').fill('Pay 1200 rupees')
    page.locator('#amount').fill('1200')
    page.locator('#run-agent').click()
    playwright.expect(page.locator('#decision')).to_be_visible()
    page.locator('#inference-details summary').click()
    playwright.expect(page.locator('#model-output')).to_have_text(raw)
    playwright.expect(page.locator('#model-input')).to_contain_text('Pay 1200 rupees')
    playwright.expect(page.locator('#inference-meta')).to_contain_text('42')
