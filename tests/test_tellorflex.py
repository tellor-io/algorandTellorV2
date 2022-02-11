from dataclasses import dataclass
from pyteal import Balance
import pytest
from scripts.scripts import Scripts
from utils.helpers import _algod_client, call_sandbox_command
from utils.helpers import add_standalone_account
from utils.testing.resources import getTemporaryAccount
from utils.util import getAppGlobalState
from algosdk import account, encoding
from algosdk.error import AlgodHTTPError

class Accounts:

    def __init__(self, client) -> None:
        self.tipper = getTemporaryAccount(client)
        self.reporter = getTemporaryAccount(client)
        self.governance = getTemporaryAccount(client)
        self.bad_actor = getTemporaryAccount(client)

class App:

    def __init__(self, id, state) -> None:
        self.id = id
        self.state = state

def setup_module(module):
    """Ensure Algorand Sandbox is up prior to running tests from this module."""
    call_sandbox_command("up")

@pytest.fixture
def client():
    client = _algod_client()
    client.flat_fee = True
    client.fee =1000
    print("fee ", client.fee)
    return client

@pytest.fixture(autouse=True)
def accounts(client):
    return Accounts(client)

@pytest.fixture(autouse=True)
def scripts(client, accounts):

    return Scripts(client=client,
                    tipper=accounts.tipper,
                    reporter=accounts.reporter,
                    governance_address=accounts.governance,
                )

@pytest.fixture(autouse=True)
def deployed_contract(accounts, client, scripts):

    query_id = "1"
    query_data = "this is my description of query_id 1"

    appID = scripts.deploy_tellor_flex(
            query_id=query_id,
            query_data=query_data
        )
        
    actual = getAppGlobalState(client, appID)
    expected = {
        b'governance_address': encoding.decode_address(accounts.governance.getAddress()),
        b'query_id': query_id.encode('utf-8'),
        b'query_data': query_data.encode('utf-8'),
        b'num_reports': 0,
        b'stake_amount': 100000,
        b'staking_status': 0,
        b'reporter_address': b'',
        b'tipper': encoding.decode_address(accounts.tipper.getAddress())
    }

    assert actual == expected

    return App(appID, actual)

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
    assert state[b'num_reports'] == 0 # number of reports shouldn't change. to avoid spamming governance needs to validate it by voting
    assert state[b'value'] == value

    scripts.report(query_id, value)

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b'num_reports'] == 0
    assert state[b'value'] == value


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


def test_not_staked_report_attempt(scripts, accounts, deployed_contract):
    '''Accounts should not be permitted to report
        if they have not send a stake to the contract'''

    assert deployed_contract.state[b'staking_status'] == 0
    assert deployed_contract.state[b'reporter_address'] == b''

    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id=b"1", value=b"the data I put on-chain 1234") #expect failure/reversion

def test_report_wrong_query_id(scripts, deployed_contract):
    '''Reporter should not be able to report to the wrong
       query_id. the transaction should revert if they pass in
       to report() a different query_id than the one specified
       in the contract by the tipper'''

def test_second_withdraw_attempt(scripts, client, deployed_contract):
    '''Shouldn't be able to withdraw stake from contract more than once'''
    scripts.stake()
    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b'staking_status'] == 1
    
    scripts.withdraw()
    
    with pytest.raises(AlgodHTTPError):
        scripts.withdraw()

def test_staking_after_withdrawing(scripts, client, deployed_contract):
    '''contract needs to be redeployed to be open for staking again'''
    scripts.stake()
    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b'staking_status'] == 1
    
    scripts.withdraw()
    with pytest.raises(AlgodHTTPError):
        scripts.stake() 

def test_reporting_after_withdrawing(scripts, client, deployed_contract):
    '''Reporter can't report once stake has been withdrawn'''

    scripts.stake()
    scripts.withdraw()
    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b'staking_status'] == 0
    query_id = b"1"
    value = b"the data I put on-chain 1234"
    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id, value)

def test_withdrawing_without_staking(scripts, deployed_contract):
    '''Shouldn't be able to withdraw without staking'''
    assert deployed_contract.state[b'staking_status'] == 0
    assert deployed_contract.state[b'reporter_address'] == b''

    with pytest.raises(AlgodHTTPError):
        scripts.withdraw()

def test_wrong_vote_input(scripts):
    '''checks other vote input other than 0 and 1'''
    with pytest.raises(AlgodHTTPError):
        scripts.vote(5)

def test_withdraw_after_slashing(scripts, client, deployed_contract):
    '''Reporter shouldn't be able to withdraw stake after being slashed'''
    scripts.stake()
    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b'staking_status'] == 1
    scripts.vote(0) #0 means reporter slashed
    
    with pytest.raises(AlgodHTTPError):
        scripts.withdraw()