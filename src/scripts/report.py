import os
import sys
from typing import Dict
from box import Box
from dotenv import load_dotenv
from src.assets.asset import Asset
from src.scripts.scripts import Scripts
from algosdk.v2client.algod import AlgodClient
from src.utils.account import Account

from src.utils.util import getBalances
from src.utils.configs import get_configs


def report(app_id: int, query_id: str, sources: Dict):
    load_dotenv()

    #create data feed
    asset = Asset(
        query_id=query_id,
        sources = sources
    )

    asset.update_price()
    value = asset.price

    algo_address = "http://localhost:4001"
    algo_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    client = AlgodClient(algod_address=algo_address, algod_token=algo_token)
    reporter = Account.FromMnemonic(os.getenv("REPORTER_MNEMONIC"))

    print(reporter.addr)
    print(getBalances(client, reporter.addr))

    s = Scripts(client=client, reporter=reporter, governance_address=None, tipper=None, app_id=app_id)
    s.report(query_id=query_id, value=value)
    print(f"submitted {value} to query id '{query_id}'")
    # print(f"algo explorer link: {}")

config = get_configs(sys.argv[1:])
print(config.app_id)
report(config.app_id.testnet, query_id=config.query_id, sources=config.apis[config.query_id])
