"""
deployment script for creating a Tellor multisig on Algorand
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

def setup_multisig(network: str):
    '''setup and deploy a multisig for Tellor'''

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