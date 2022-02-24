import os
import sys

from algosdk.v2client.algod import AlgodClient
from dotenv import load_dotenv

from src.scripts.scripts import Scripts
from src.utils.account import Account
from src.utils.configs import get_configs
from src.utils.util import getBalances


def stake(app_id: int):
    load_dotenv()

    algo_address = "http://localhost:4001"
    algo_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    client = AlgodClient(algod_address=algo_address, algod_token=algo_token)
    reporter = Account.FromMnemonic(os.getenv("REPORTER_MNEMONIC"))

    print(reporter.addr)
    print(getBalances(client, reporter.addr))

    s = Scripts(client=client, reporter=reporter, governance_address=None, tipper=None, app_id=app_id)
    s.stake()


config = get_configs(sys.argv[1:])
stake(config.app_id.testnet)
