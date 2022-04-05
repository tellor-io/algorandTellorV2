import time

import pytest
from algosdk import encoding
from algosdk.logic import get_application_address
from src.utils.util import getAppGlobalState
from src.scripts.scripts import Scripts


def test_activate_contract(client, scripts: Scripts, accounts, deployed_contract):
    """Test activate_contract method on medianizer_contract"""

    medianzier_state = getAppGlobalState(client, deployed_contract.medianizer_id)
    n = 1
    for i in deployed_contract.feed_ids:
        feed_state = getAppGlobalState(client, i)
        app = "app_" + f"{n}"
        encoded = app.encode('utf-8')
        addr = get_application_address(i)
        n+=1
        assert medianzier_state[encoded] == encoding.decode_address(addr)
        assert feed_state[b"medianizer"] == deployed_contract.medianizer_id

    assert medianzier_state[b"governance"] == encoding.decode_address(accounts.governance.address())


def test_get_values(client, scripts: Scripts, accounts, deployed_contract):
    """Test get_values() method on medianizer_contract"""

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)
    
    feed_state = getAppGlobalState(client, feed_id)
    assert feed_state[b"reporter_address"] == b""

    scripts.tip(300000)
    scripts.stake()

    feed_state = getAppGlobalState(client, feed_id)
    assert feed_state[b"staking_status"] == 1
    assert feed_state[b"reporter_address"] == encoding.decode_address(accounts.reporter.getAddress())

    query_id = b"1"
    value = 1234
    timestamp = 5678
    scripts.report(query_id, value, timestamp)
    medianizer_state = getAppGlobalState(client, deployed_contract.medianizer_id)
    assert feed_state[b"query_id"] == query_id
    assert medianizer_state[b"median"] == value
    assert medianizer_state[b"median_timestamp"] == timestamp

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
