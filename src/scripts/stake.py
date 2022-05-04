import os
import sys
from typing import Optional

from dotenv import load_dotenv

from src.scripts.scripts import Scripts
from src.utils.account import Account
from src.utils.configs import get_configs
from src.utils.testing.setup import getAlgodClient
from src.utils.util import getBalances


def stake(app_id: Optional[int], network: str):
    load_dotenv()
    client = getAlgodClient()

    print("current network: ", network)
    reporter = Account.FromMnemonic(os.getenv("REPORTER_MNEMONIC"))

    print("staker balance", getBalances(client, reporter.addr))
    print("staking at reporter address: ", reporter.addr)

    s = Scripts(client=client, reporter=reporter, governance_address=None, tipper=None, feed_app_id=app_id)
    s.stake()

    print(f"account at {reporter.addr} is now a tellor {network} reporter on app id {app_id}")


if __name__ == "__main__":

    # read config
    config = get_configs(sys.argv[1:])

    # parse app_ids of query_id from config
    app_ids = config.feeds[config.query_id].app_ids.feeds[config.network]
    stake(app_ids[1], config.network)
