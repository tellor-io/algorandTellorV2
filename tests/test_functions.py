from utils.util import getAppGlobalState
from algosdk import encoding

from conftest import *



def test_stake(client, scripts, accounts, deployed_contract):

    stake_amount = 100000

    reporter_algo_balance_before = client.account_info(accounts.reporter.getAddress()).get("amount")
    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b'staking_status'] == 0
    assert state[b'reporter_address'] == b''

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b'staking_status'] == 1
    assert state[b'reporter_address'] == encoding.decode_address(accounts.reporter.getAddress())

    reporter_algo_balance_after = client.account_info(accounts.reporter.getAddress()).get("amount")
    assert reporter_algo_balance_after == reporter_algo_balance_before - stake_amount - client.fee*2

def test_report(client, scripts, accounts, deployed_contract):

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b'num_reports'] == 0

    query_id = b"1"
    value = b"the data I put on-chain 1234"
    scripts.report(query_id, value)

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b'num_reports'] == 1
    assert state[b'value'] == value

    scripts.report(query_id, value)

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b'num_reports'] == 2
    assert state[b'value'] == value


def test_withdraw():
    pass

def test_vote():
    pass