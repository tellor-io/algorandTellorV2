"""
deployment script for testnet or devnet
"""
import os
import sys

from algosdk.error import AlgodHTTPError
from algosdk.future.transaction import Multisig
from algosdk.v2client.algod import AlgodClient
from dotenv import load_dotenv

from src.scripts.scripts import Scripts
from src.utils.account import Account
from src.utils.configs import get_configs
from src.utils.testing.resources import fundAccount
from src.utils.testing.resources import getTemporaryAccount


def deploy(query_id: str, query_data: str, timestamp_freshness: int, network: str):
    """
    quick deployment scheme, works on:
    - local private network
    - algorand public testnet
    """

    load_dotenv()
    if network == "testnet":
        algo_address = "http://testnet-api.algonode.network"
        algo_token = ""
    elif network == "mainnet":
        algo_address = "http://mainnet-api.algonode.network"
        algo_token = ""
    else:
        algo_address = "http://localhost:4001"
        algo_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    client = AlgodClient(algod_address=algo_address, algod_token=algo_token)

    print("current network: ", network)
    if network in ["testnet", "mainnet"]:
        tipper = Account.FromMnemonic(os.getenv("TIPPER_MNEMONIC"))
        reporter = Account.FromMnemonic(os.getenv("REPORTER_MNEMONIC"))
        member_1 = Account.FromMnemonic(os.getenv("MEMBER_1").replace(",", ""))
        member_2 = Account.FromMnemonic(os.getenv("MEMBER_2").replace(",", ""))
        multisig_accounts_pk = [member_1.addr, member_2.addr]
        multisig_accounts_sk = [member_1.getPrivateKey(), member_2.getPrivateKey()]
        governance = Multisig(version=1, threshold=2, addresses=multisig_accounts_pk)

        if network == "testnet":
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
        fundAccount(client, tipper.addr)
        fundAccount(client, member_1.addr)
        fundAccount(client, member_2.addr)
    else:
        raise Exception("invalid network selected")

    s = Scripts(
        client=client, tipper=tipper, reporter=reporter, governance_address=governance.address(), contract_count=5
    )

    try:
        tellor_flex_app_id = s.deploy_tellor_flex(
            query_id=query_id,
            query_data=query_data,
            multisigaccounts_sk=multisig_accounts_sk,
            timestamp_freshness=timestamp_freshness,
        )
    except AlgodHTTPError as e:
        if "pc=763" in str(e):
            raise ValueError("timestamp freshness (-tf) must be >= 120")

    medianizer_app_id = s.deploy_medianizer(
        timestamp_freshness=timestamp_freshness, multisigaccounts_sk=multisig_accounts_sk, query_id=query_id
    )

    activate_medianizer = s.activate_contract(multisigaccounts_sk=multisig_accounts_sk)

    change_medianizer = s.change_medianizer(multisigaccounts_sk=multisig_accounts_sk)
    print(f"TellorFlex App deployed on {network}. App id: {tellor_flex_app_id}")
    print(f"Medianizer App deployed on {network}. App id: {medianizer_app_id}")
    print(f"Medianizer activate, Txn id: {activate_medianizer}")
    print(f"Set Medianizer on feeds, Txn id: {change_medianizer}")
    # print("please update config.yaml with new app_id.")


config = get_configs(sys.argv[1:])
deploy(
    query_id=config.query_id,
    query_data=config.query_data,
    timestamp_freshness=config.timestamp_freshness,
    network=config.network,
)
