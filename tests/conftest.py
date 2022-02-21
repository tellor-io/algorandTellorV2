import pytest
from algosdk import encoding

from src.scripts.scripts import Scripts
from src.utils.accounts import Accounts
from src.utils.helpers import _algod_client
from src.utils.util import getAppGlobalState

# from src.utils.helpers import call_sandbox_command


class App:
    """simple class for contract metadata"""

    def __init__(self, id: int, state) -> None:
        """
        id (int): the application id
        state: state of the contract
        """
        self.id = id
        self.state = state


# def setup_module(module):
#     """Ensure Algorand Sandbox is up prior to running tests from this module."""
#     call_sandbox_command("up")


@pytest.fixture
def client():
    """AlgodClient for testing"""
    client = _algod_client()
    client.flat_fee = True
    client.fee = 1000
    print("fee ", client.fee)
    return client


@pytest.fixture(autouse=True)
def accounts(client):
    """provides easy account access for testing"""
    return Accounts(client)


@pytest.fixture(autouse=True)
def scripts(client, accounts):
    """Scripts object for testing"""

    return Scripts(
        client=client,
        tipper=accounts.tipper,
        reporter=accounts.reporter,
        governance_address=accounts.governance,
    )


@pytest.fixture(autouse=True)
def deployed_contract(accounts, client, scripts):
    """deploys contract, provides app id and state for testing"""

    query_id = "1"
    query_data = "this is my description of query_id 1"

    appID = scripts.deploy_tellor_flex(query_id=query_id, query_data=query_data)

    actual = getAppGlobalState(client, appID)
    expected = {
        b"governance_address": encoding.decode_address(accounts.governance.getAddress()),
        b"query_id": query_id.encode("utf-8"),
        b"query_data": query_data.encode("utf-8"),
        b"num_reports": 0,
        b"stake_amount": 200000,
        b"staking_status": 0,
        b"reporter_address": b"",
        b"tipper": encoding.decode_address(accounts.tipper.getAddress()),
    }

    assert actual == expected

    return App(appID, actual)
