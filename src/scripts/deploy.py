"""
deployment script for testnet or devnet
"""
import os
import sys

from algosdk.v2client.algod import AlgodClient
from dotenv import load_dotenv

from src.scripts.scripts import Scripts
from src.utils.account import Account
from src.utils.configs import get_configs
from src.utils.testing.resources import fundAccount
from src.utils.testing.resources import getTemporaryAccount


def deploy(query_id: str, query_data: str, network: str):
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
        reporter = Account.FromMnemonic(os.getenv("REPORTER_MNEMONIC"))
    elif network == "devnet":
        tipper = getTemporaryAccount(client)
        reporter = getTemporaryAccount(client)
        governance = getTemporaryAccount(client)

        fundAccount(client, reporter.addr)
        fundAccount(client, reporter.addr)
        fundAccount(client, reporter.addr)
    else:
        raise Exception("invalid network selected")

    s = Scripts(client=client, tipper=tipper, reporter=reporter, governance_address=governance)

    app_id = s.deploy_tellor_flex(
        query_id=query_id,
        query_data=query_data,
    )

    print(f"App deployed on {network}. App id: ", app_id)
    print("please update config.yaml with new app_id.")


config = get_configs(sys.argv[1:])
deploy(query_id=config.query_id, query_data=config.query_data, network=config.network)
