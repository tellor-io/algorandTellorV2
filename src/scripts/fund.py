import os

from algosdk.v2client.algod import AlgodClient
from dotenv import load_dotenv

from src.utils.account import Account
from src.utils.testing.resources import fundAccount


def fund_devnet_accounts():
    """
    Funds accounts listed in .env file
    ONLY WORKS ON DEVNET
    """
    load_dotenv()

    algo_address = "http://localhost:4001"
    algo_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    client = AlgodClient(algod_address=algo_address, algod_token=algo_token)

    reporter = Account.FromMnemonic(os.getenv("REPORTER_MNEMONIC"))
    tipper = Account.FromMnemonic(os.getenv("TIPPER_MNEMONIC"))
    governance = Account.FromMnemonic(os.getenv("GOVERNANCE_MNEMONIC"))

    accounts = [reporter, tipper, governance]

    for i in accounts:
        fundAccount(client, i.addr)

    print("devnet accounts funded")


fund_devnet_accounts()
