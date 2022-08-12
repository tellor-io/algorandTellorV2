import os
import sys

from dotenv.main import load_dotenv

from src.scripts.scripts import Scripts
from src.utils.account import Account
from src.utils.configs import get_configs
from src.utils.testing.setup import getAlgodClient


def tip(app_id: int, amount: int, network: str):
    load_dotenv()

    client = getAlgodClient(network)
    print("current network: ", network)
    tipper = Account.FromMnemonic(os.getenv("TIPPER_MNEMONIC"))

    s = Scripts(client=client, tipper=tipper, reporter=None, governance_address=None, feed_app_id=app_id)
    s.tip(amount)


if __name__ == "__main__":

    # read config
    config = get_configs(sys.argv[1:])
    # parse app_ids of query_id from config
    app_ids = config.feeds[config.query_id].app_ids.feeds[config.network]

    print(f"now tipping this query_id: {config.query_id}, on feed_id: {app_ids[config.feed_index]}")

    tip(app_id=app_ids[config.feed_index], amount=config.amount, network=config.network)
