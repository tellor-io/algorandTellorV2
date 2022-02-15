from utils.util import getAppGlobalState
from algosdk import encoding

from conftest import *


def test_report(client, scripts, accounts, deployed_contract):

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b'num_reports'] == 0

    query_id = b"1"
    value = b"the data I put on-chain 1234"
    scripts.report(query_id, value)

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b'num_reports'] == 0 #won't increment until approved by governance
    assert state[b'value'] == value

    new_value = b"a new data value 4567"
    scripts.report(query_id, new_value)

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b'num_reports'] == 0 #won't increment until approved by governance
    assert state[b'value'] == new_value

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


def test_vote(client, scripts, accounts, deployed_contract):
    scripts.stake()
    state = getAppGlobalState(client, deployed_contract.id)
    num_reports = state[b'num_reports']
    scripts.vote(1)

    state = getAppGlobalState(client, deployed_contract.id)
    num_reports+=1 #number of reports increases by 1
    assert state[b'num_reports'] == num_reports
    assert state[b'staking_status'] == 1

    scripts.vote(0)
    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b'num_reports'] == num_reports #number of reports doesn't increase nor decrease after slashing
    assert state[b'staking_status'] == 0

def test_withdraw(client, scripts, accounts, deployed_contract):
    
    reporter_algo_balance_before = client.account_info(accounts.reporter.getAddress()).get("amount")
    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b'staking_status'] == 0

    scripts.stake()
    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b'staking_status'] == 1

    tx_fee = 2000
    scripts.withdraw()
    state = getAppGlobalState(client, deployed_contract.id)

    reporter_algo_balance_after = client.account_info(accounts.reporter.getAddress()).get("amount")
    
    assert state[b'staking_status'] == 0
    assert reporter_algo_balance_after == reporter_algo_balance_before - tx_fee*2
