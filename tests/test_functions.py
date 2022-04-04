import time

import pytest
from algosdk import encoding
from algosdk.logic import get_application_address

from src.utils.util import getAppGlobalState


def test_activate_contract(client, scripts, accounts, deployed_contract, deployed_medianizer_contract):
    """Test activate_contract method on medianizer_contract"""

    medianzier_state = getAppGlobalState(client, deployed_medianizer_contract.id)
    # app addresses should be null initially
    assert medianzier_state[b"app_1"] == ""
    assert medianzier_state[b"app_2"] == ""
    assert medianzier_state[b"app_3"] == ""
    assert medianzier_state[b"app_4"] == ""
    assert medianzier_state[b"app_5"] == ""
    assert medianzier_state[b"governance"] == encoding.decode_address(accounts.governance.address())

    scripts.activate_contract(accounts.multisig_signers_sk)

    # apps should be
    app_addr_1 = get_application_address(deployed_contract.id)
    assert medianzier_state[b"app_1"] == app_addr_1
    # assert medianzier_state[b"app_2"] == app_addr_2
    # assert medianzier_state[b"app_3"] == app_addr_3
    # assert medianzier_state[b"app_4"] == app_addr_4
    # assert medianzier_state[b"app_5"] == app_addr_5
    assert medianzier_state[b"governance"] == encoding.decode_address(accounts.governance.address())


def test_get_values(client, scripts, accounts, deployed_contract, deployed_medianizer_contract):
    """Test get_values() method on medianizer_contract"""
    medianzier_state = getAppGlobalState(client, deployed_medianizer_contract.id)
    feed_state = getAppGlobalState(client, deployed_contract.id)
    scripts.stake()
    assert feed_state[b"num_reports"] == 0

    query_id = b"1"
    value = 1234
    timestamp = 5678
    scripts.report(query_id, value, timestamp)
    assert feed_state[b"query_id"] == query_id
    assert feed_state[b"value"] == value
    assert feed_state[b"timestamp"] == timestamp

    scripts.get_values()
    assert medianzier_state["median_price"] == value
    assert medianzier_state["median_timestamp"] == timestamp


def test_report(client, scripts, accounts, deployed_contract):
    """Test report() method on contract"""

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"num_reports"] == 0

    query_id = b"1"
    value = b"the data I put on-chain 1234"
    scripts.report(query_id, value)

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"num_reports"] == 0  # won't increment until approved by governance
    assert state[b"value"] == value
    assert pytest.approx(state[b"timestamp"], 100) == int(time.time())

    new_value = b"a new data value 4567"
    scripts.report(query_id, new_value)

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"num_reports"] == 0  # won't increment until approved by governance
    assert state[b"value"] == new_value
    assert pytest.approx(state[b"timestamp"], 100) == int(time.time())


def test_stake(client, scripts, accounts, deployed_contract):
    """Test stake() method on contract"""

    stake_amount = 200000

    reporter_algo_balance_before = client.account_info(accounts.reporter.getAddress()).get("amount")
    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b"staking_status"] == 0
    assert state[b"reporter_address"] == b""

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b"staking_status"] == 1
    assert state[b"reporter_address"] == encoding.decode_address(accounts.reporter.getAddress())

    reporter_algo_balance_after = client.account_info(accounts.reporter.getAddress()).get("amount")
    assert reporter_algo_balance_after == reporter_algo_balance_before - stake_amount - client.fee * 2


def test_vote(client, scripts, accounts, deployed_contract):
    """Test vote() method on contract"""
    scripts.stake()
    state = getAppGlobalState(client, deployed_contract.id)
    num_reports = state[b"num_reports"]
    scripts.vote(1)

    state = getAppGlobalState(client, deployed_contract.id)
    num_reports += 1  # number of reports increases by 1
    assert state[b"num_reports"] == num_reports
    assert state[b"staking_status"] == 1

    scripts.vote(0)
    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"num_reports"] == num_reports  # number of reports doesn't increase nor decrease after slashing
    assert state[b"staking_status"] == 0


def test_request_withdraw(client, scripts, accounts, deployed_contract):
    """Test request_withdraw() method on feed contract"""

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.id)

    # assert staking status before fn call is 1
    assert state[b"staking_status"] == 1

    # assert stake_timestamp is 0
    assert state[b"stake_timestamp"] == 0

    # call request_withdraw
    scripts.request_withdraw()

    # get state again
    state = getAppGlobalState(client, deployed_contract.id)

    # assert stake timestamp is now approx. time.time()
    assert state[b"stake_timestamp"] == pytest.approx(time.time(), 500)

    # assert staking status is now 2
    assert state[b"staking_status"] == 2


def test_withdraw(client, scripts, accounts, deployed_contract):
    """test withdraw() method on contract"""

    reporter_algo_balance_before = client.account_info(accounts.reporter.getAddress()).get("amount")
    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b"staking_status"] == 0

    scripts.stake()
    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b"staking_status"] == 1

    scripts.request_withdraw()

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"staking_status"] == 2

    tx_fee = 2000

    state = getAppGlobalState(client, deployed_contract.id)

    reporter_algo_balance_after = client.account_info(accounts.reporter.getAddress()).get("amount")

    assert state[b"staking_status"] == 0
    assert reporter_algo_balance_after == reporter_algo_balance_before - tx_fee * 2
