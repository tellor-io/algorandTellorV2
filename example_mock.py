from time import time, sleep

from algosdk import account, encoding
from algosdk.logic import get_application_address
from pyteal import Txn
from scripts.deploy import Scripts
from utils.util import (
    getBalances,
    getAppGlobalState,
    getLastBlockTimestamp,
)
from utils.helpers import _algod_client
from utils.testing.resources import (
    getTemporaryAccount,
    optInToAsset,
    createDummyAsset,
)

def simple_oracle():
    client = _algod_client()
    # client.flat_fee = True
    # client.fee =1000
    # print("fee ",client.fee)
    print("Generating temporary accounts...")
    tipper = getTemporaryAccount(client)
    reporter = getTemporaryAccount(client)
    governance_address = getTemporaryAccount(client)

    print("(tipper account): ", tipper.getAddress(), "account balance: ",getBalances(client, tipper.getAddress()))
    print("(reporter account): ", reporter.getAddress(), "account balance: ",getBalances(client, reporter.getAddress()))
    print("(governance_address account): ", governance_address.getAddress(), "account balance: ", getBalances(client, governance_address.getAddress()), "\n")

    construct = Scripts(client=client,
                        tipper=tipper,
                        reporter=reporter,
                        governance_address=governance_address
                        )

    query_id = 'hi'
    query_data = 'hi'

    appID = construct.deploy_tellor_flex(
        query_id=query_id,
        query_data=query_data
    )
    
    actual = getAppGlobalState(client, appID)
    
    expected = {
        b'governance_address': encoding.decode_address(governance_address.getAddress()),
        b'query_id': query_id.encode('utf-8'),
        b'query_data': query_data.encode('utf-8'),
        b'num_reports': 0,
        b'stake_amount': 100000,
        b'staking_status': 0,
        b'tipper': encoding.decode_address(tipper.getAddress())
    }
    print("Done deploying")
    assert actual == expected
    
    # reporter balance before staking
    balance_before = getBalances(client, reporter.getAddress())[0]
    
    # reporter staking
    construct.stake()

    print(getBalances(client, reporter.getAddress())[0])
    #reporter balance should their before balance minus the stake amount minus txn fee (2000 if not set to Global.min_txn_fee())
    assert getBalances(client, reporter.getAddress())[0] == balance_before - getAppGlobalState(client, appID)[bytes('stake_amount','utf-8')] - 2000
    # currently_staked turns to 1 when reporter stakes but staking_status is still 0...?
    assert getAppGlobalState(client,appID)[bytes('currently_staked','utf-8')] == 1
    print("(reporter account):", reporter.getAddress(), "account balance: ",getBalances(client, reporter.getAddress()))
    # can't stake again gets error has already opted in to app ID!
    construct.stake()



simple_oracle()