from time import time

import pytest
from algosdk import constants, encoding
from algosdk.logic import get_application_address
from src.utils.util import getAppGlobalState
from src.utils.accounts import Accounts
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
    value = 3500
    timestamp = int(time()-500)

    scripts.report(query_id, value, timestamp)

    medianizer_state = getAppGlobalState(client, deployed_contract.medianizer_id)

    assert feed_state[b"query_id"] == query_id
    assert medianizer_state[b"median"] == value
    assert medianizer_state[b"median_timestamp"] == timestamp

def test_report(client, scripts: Scripts, accounts, deployed_contract):
    """Test report() method on contract"""
    tip = 100000
    for i in deployed_contract.feed_ids:
        scripts.feed_app_id = i
        feed_id = scripts.feed_app_id
        scripts.feed_app_address = get_application_address(feed_id)

        scripts.tip(tip)
        scripts.stake()
        
        state = getAppGlobalState(client, i)
        assert state[b"reporter_address"] ==  encoding.decode_address(accounts.reporter.getAddress())
        assert state[b"staking_status"] ==  1

        query_id = b"1"
        value = 3450
        timestamp = int(time()-1000)
        reporter_balance_before = client.account_info(accounts.reporter.getAddress()).get("amount")
        
        assert state[b"tip_amount"] == tip
        governance_balance_before = client.account_info(accounts.governance.address()).get("amount")
        scripts.report(query_id, value, timestamp)
        
        state = getAppGlobalState(client, i)
        reporter_balance_after = client.account_info(accounts.reporter.getAddress()).get("amount")
        governance_balance_after = client.account_info(accounts.governance.address()).get("amount")
        
        encoded = int.to_bytes(timestamp,length=8,byteorder='big')+int.to_bytes(value,length=8,byteorder='big')
        assert state[b"last_value"] == encoded
        assert reporter_balance_after == (reporter_balance_before+int(tip*.98))-(constants.MIN_TXN_FEE)
        assert governance_balance_after == (governance_balance_before+(tip*.02))
        assert state[b"tip_amount"] == 0


def test_stake(client, scripts, accounts, deployed_contract):
    """Test stake() method on contract"""
    client.suggested_params().flatFee = True;
    client.suggested_params().fee = 2 * constants.MIN_TXN_FEE;
    stake_amount = 200000
    for i in deployed_contract.feed_ids:
        scripts.feed_app_id = i
        feed_id = scripts.feed_app_id
        scripts.feed_app_address = get_application_address(feed_id)

        reporter_algo_balance_before = client.account_info(accounts.reporter.getAddress()).get("amount")
        state = getAppGlobalState(client, i)

        assert state[b"staking_status"] == 0
        assert state[b"reporter_address"] == b""

        scripts.stake()

        state = getAppGlobalState(client, i)

        assert state[b"staking_status"] == 1
        assert state[b"reporter_address"] == encoding.decode_address(accounts.reporter.getAddress())
        
        reporter_algo_balance_after = client.account_info(accounts.reporter.getAddress()).get("amount")
        assert reporter_algo_balance_after == reporter_algo_balance_before - stake_amount - (2*constants.MIN_TXN_FEE)

def test_slash_reporter(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Test slash_reporter() method on contract"""
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    state[b"staking_status"] == 1
    governance_algo_balance_before = client.account_info(accounts.governance.address()).get("amount")

    scripts.slash_reporter(multisigaccounts_sk=accounts.multisig_signers_sk)

    governance_algo_balance_after = client.account_info(accounts.governance.address()).get("amount")
    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 0
    assert state[b"reporter_address"] == b""
    assert governance_algo_balance_after == governance_algo_balance_before + state[b"stake_amount"] - (2*constants.MIN_TXN_FEE)



def test_request_withdraw(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Test request_withdraw() method on feed contract"""
    # set feed id for app to test request_withdraw()
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id

    # set feed app address
    scripts.feed_app_address = get_application_address(feed_id)

    # stake reporter
    scripts.stake()

    # get state of feed app after staking reporter
    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    # assert staking status before fn call is 1
    assert state[b"staking_status"] == 1

    # assert stake_timestamp is 0
    assert state[b"stake_timestamp"] == 0

    # call request_withdraw
    scripts.request_withdraw()

    # get state again
    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    # assert stake timestamp is now approx. time.time()
    assert state[b"stake_timestamp"] == pytest.approx(int(time()), 500)

    # assert staking status is now 2
    assert state[b"staking_status"] == 2


def test_withdraw(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """test withdraw() method on contract"""
    #   set feed id for app to test withdraw()
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id

    # set feed app address
    scripts.feed_app_address = get_application_address(feed_id)

    state = getAppGlobalState(client, deployed_contract.feed_ids[0]) 

    assert state[b"staking_status"] == 0

    # stake reporter
    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 1

    scripts.request_withdraw()

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    
    # assert staking status changed to 2 meaning withdrawal requested
    assert state[b"staking_status"] == 2

    tx_fee = 2000

    # get reporter's balance before withdrawal
    reporter_algo_balance_before = client.account_info(accounts.reporter.getAddress()).get("amount")

    # dryrun withdrawal after 7 days
    res = scripts.withdraw_dry(timestamp= int(time())+604800)

    assert encoding.base64.b64encode(b"staking_status").decode('utf-8') == res['txns'][0]['global-delta'][0]['key'] 
    assert res['txns'][0]['global-delta'][0]['value']['uint'] == 0
    assert encoding.base64.b64encode(b"stake_timestamp").decode('utf-8') == res['txns'][0]['global-delta'][1]['key']
    assert res['txns'][0]['global-delta'][1]['value']['uint'] == 0

    # get state after withdrawal
    # state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    # get reporter's balance after withdraw
    # reporter_algo_balance_after = client.account_info(accounts.reporter.getAddress()).get("amount")

    # assert state[b"staking_status"] == 0
    # assert reporter_algo_balance_after == reporter_algo_balance_before - tx_fee * 2
