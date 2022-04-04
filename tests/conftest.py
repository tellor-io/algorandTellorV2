import pytest
from algosdk import encoding

from src.scripts.scripts import Scripts
from src.utils.accounts import Accounts
from src.utils.helpers import _algod_client
from src.utils.util import getAppGlobalState
from algosdk.logic import get_application_address
from src.utils.testing.resources import fundAccount

# from src.utils.helpers import call_sandbox_command


class App:
    """simple class for contract metadata"""

    def __init__(self, feed_ids: list, medianizer_id: int) -> None:
        """
        feed_ids (list): a list of feed application ids
        medianizer_id: int (int): medianizer application id
        """
        self.feed_ids = feed_ids
        self.medianizer_id = medianizer_id


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
        contract_count=5
    )


@pytest.fixture(autouse=True)
def deployed_contract(accounts, client, scripts):
    """deploys feeds and medianizer contracts, provides app ids for all contracts"""

    fundAccount(client, accounts.governance.address())
    fundAccount(client, accounts.tipper.address())
    fundAccount(client, accounts.reporter.address())

    query_id = "1"
    query_data = "this is my description of query_id 1"

    feedAppIDs = scripts.deploy_tellor_flex(
        query_id=query_id, query_data=query_data, multisigaccounts_sk=accounts.multisig_signers_sk
    )

    for ids in feedAppIDs:
        actual = getAppGlobalState(client, ids)
        expected = {
            b"governance_address": encoding.decode_address(accounts.governance.address()),
            b"query_id": query_id.encode("utf-8"),
            b"query_data": query_data.encode("utf-8"),
            b"medianizer": 0,
            b"timestamps": b"",
            b"stake_amount": 200000,
            b"staking_status": 0,
            b"stake_timestamp": 0,
            b"reporter_address": b"",
            b"values": b"",
            b"tip_amount": 0
        }

        assert actual == expected

    time_interval = 1234567
    medianizerAppID = scripts.deploy_medianizer(time_interval=time_interval, multisigaccounts_sk=accounts.multisig_signers_sk)

    scripts.activate_contract(multisigaccounts_sk=accounts.multisig_signers_sk)
    scripts.set_medianizer(multisigaccounts_sk=accounts.multisig_signers_sk)
    
    medianizerState = getAppGlobalState(client, medianizerAppID)
    feedState1 = getAppGlobalState(client, feedAppIDs[0])
    feedAddr1 = get_application_address(feedAppIDs[0])

    assert medianizerState[b"app_1"] == encoding.decode_address(feedAddr1)
    assert feedState1[b"medianizer"] == medianizerAppID

    return App(feedAppIDs, medianizerAppID)
