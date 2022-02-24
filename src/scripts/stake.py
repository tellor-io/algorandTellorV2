import os
from dotenv import load_dotenv
from src.scripts.scripts import Scripts
from algosdk.v2client.algod import AlgodClient
from src.utils.account import Account

from src.utils.util import getAppGlobalState, getBalances

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

stake(73661747)