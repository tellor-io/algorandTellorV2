import pytest
from scripts.scripts import Scripts
from utils.helpers import _algod_client, call_sandbox_command
from utils.testing.resources import getTemporaryAccount
from utils.util import getAppGlobalState
from algosdk import encoding


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