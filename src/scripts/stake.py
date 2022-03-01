import os
import sys
from typing import Optional

from algosdk.v2client.algod import AlgodClient
from dotenv import load_dotenv

from src.scripts.scripts import Scripts
from src.utils.account import Account
from src.utils.configs import get_configs
from src.utils.util import getBalances


def stake(app_id: Optional[int], network: str):
    load_dotenv()

    algo_address = "http://localhost:4001"
    algo_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    client = AlgodClient(algod_address=algo_address, algod_token=algo_token)

    print("current network: ", network)
    reporter = Account.FromMnemonic(os.getenv("REPORTER_MNEMONIC"))

    print("staker balance", getBalances(client, reporter.addr))
    print("staking at reporter address: ", reporter.addr)

    s = Scripts(client=client, reporter=reporter, governance_address=None, tipper=None, app_id=app_id)
    s.stake()

    print(f"account at {reporter.addr} is now a tellor {network} reporter on app id {app_id}")


config = get_configs(sys.argv[1:])
stake(config.app_id[config.network], config.network)
