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
    """
    quick deployment scheme, works on:
    - local private network
    - algorand public testnet
    """

    load_dotenv()

    algo_address = "http://localhost:4001"
    algo_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    client = AlgodClient(algod_address=algo_address, algod_token=algo_token)

    print("current network: ", network)
    if network == "testnet":
        tipper = Account.FromMnemonic(os.getenv("TIPPER_MNEMONIC"))
        reporter = Account.FromMnemonic(os.getenv("REPORTER_MNEMONIC"))
        member_1 = Account.FromMnemonic(os.getenv("MEMBER_1"))
        member_2 = Account.FromMnemonic(os.getenv("MEMBER_2"))
        multisig_accounts = [member_1, member_2]
        governance = Multisig(version=1, threshold=2, addresses=multisig_accounts)
        print("Multisig Address: ", governance.address())
        print(
            "Go to the below link to fund the created account using testnet faucet: \
            \n https://dispenser.testnet.aws.algodev.network/?account={}".format(
                governance.address()
            )
        )
        input("Press Enter to continue...")
    elif network == "devnet":
        tipper = getTemporaryAccount(client)
        reporter = getTemporaryAccount(client)
        member_1 = getTemporaryAccount(client)
        member_2 = getTemporaryAccount(client)
        multisig_accounts_pk = [member_1.addr, member_2.addr]
        multisig_accounts_sk = [member_1.getPrivateKey(), member_2.getPrivateKey()]

        governance = Multisig(version=1, threshold=2, addresses=multisig_accounts_pk)
        fundAccount(client, governance.address())
        fundAccount(client, reporter.addr)
        fundAccount(client, reporter.addr)
        fundAccount(client, reporter.addr)
    else:
        raise Exception("invalid network selected")

    s = Scripts(client=client, tipper=tipper, reporter=reporter, governance_address=governance, contract_count=5)

    tellor_flex_app_id = s.deploy_tellor_flex(
        query_id=query_id, query_data=query_data, multisigaccounts_sk=multisig_accounts_sk
    )
    medianizer_app_id = s.deploy_medianizer(time_interval=time_interval, multisigaccounts_sk=multisig_accounts_sk)

    activate_medianizer = s.activate_contract(multisigaccounts_sk=multisig_accounts_sk)

    set_medianizer = s.set_medianizer(multisigaccounts_sk=multisig_accounts_sk)