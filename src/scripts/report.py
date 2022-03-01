import os
import sys
from typing import Dict

from algosdk.v2client.algod import AlgodClient
from dotenv import load_dotenv

from src.assets.asset import Asset
from src.scripts.scripts import Scripts
from src.utils.account import Account
from src.utils.configs import get_configs
from src.utils.util import getBalances


def report(app_id: int, query_id: str, network: str, sources: Dict):
    load_dotenv()

    # create data feed
    asset = Asset(query_id=query_id, sources=sources)

    asset.update_price()
    value = asset.price

    algo_address = "http://localhost:4001"
    algo_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    client = AlgodClient(algod_address=algo_address, algod_token=algo_token)

    print("current network: ", network)
    reporter = Account.FromMnemonic(os.getenv("REPORTER_MNEMONIC"))

    print("reporter address:", reporter.addr)
    print("reporter's microAGLO balance:", getBalances(client, reporter.addr)[0])

    print(f"reporting value '{value}' to query id '{query_id}'")

    s = Scripts(client=client, reporter=reporter, governance_address=None, tipper=None, app_id=app_id)
    s.report(query_id=query_id, value=value)
    print(f"submitted value '{value}' to query id '{query_id}'")
    # print(f"algo explorer link: {}")


config = get_configs(sys.argv[1:])
print("app id: ", config.app_id[config.network])

report(
    app_id=config.app_id[config.network],
    query_id=config.query_id,
    network=config.network,
    sources=config.apis[config.query_id],
)
