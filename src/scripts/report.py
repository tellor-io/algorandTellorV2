import os
import sys
from time import time
from typing import Dict

from algosdk.v2client.algod import AlgodClient
from dotenv import load_dotenv

from src.assets.asset import Asset
from src.scripts.scripts import Scripts
from src.utils.account import Account
from src.utils.configs import get_configs
from src.utils.util import getBalances


def report(
    app_id: int, medianizer_id: int, feed_ids: list, query_id: str, network: str, governance_address: str, sources: Dict
):
    load_dotenv()

    # create data feed
    asset = Asset(query_id=query_id, sources=sources)

    asset.update_price()
    value = asset.price

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
    reporter = Account.FromMnemonic(os.getenv("REPORTER_MNEMONIC"))

    print("reporter address:", reporter.addr)
    print("reporter's microAGLO balance:", getBalances(client, reporter.addr)[0])

    s = Scripts(
        client=client,
        reporter=reporter,
        medianizer_app_id=medianizer_id,
        governance_address=governance_address,
        tipper=None,
        feed_app_id=app_id,
    )
    s.feeds = feed_ids
    s.report(query_id=query_id, value=value, timestamp=int(time() - 50))

    print(f"submitted value '{value}' to query id '{query_id}'")
    # print(f"algo explorer link: {}")


if __name__ == "__main__":

    # read config
    config = get_configs(sys.argv[1:])

    # parse app_ids of query_id from config
    app_ids = config.feeds[config.query_id].app_ids.feeds[config.network]

    report(
        app_id=app_ids[config.feed_index],
        medianizer_id=config.feeds[config.query_id].app_ids.medianizer[config.network],
        feed_ids=app_ids,
        query_id=config.query_id,
        network=config.network,
        governance_address=config.governance_address,
        sources=config.apis[config.query_id],
    )
