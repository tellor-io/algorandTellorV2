import pytest
from utils.testing.resources import getTemporaryAccount
from utils.util import getAppGlobalState
from algosdk import encoding
from algosdk.error import AlgodHTTPError

from conftest import *

def test_demo(client, scripts):

    print("TELLOR APPLICATION WALKTHROUGH")

    print("deployment...")
    #deploy contract
    app_id = scripts.deploy_tellor_flex(
        query_id="btc/usd",
        query_data="I need a btc/usd spot price feed"
    )

    print("contract deployed! application id: ", app_id)

    #print contract attributes
    state = getAppGlobalState(client, appID=app_id)
    tipper = encoding.encode_address(state[b'tipper'])
    query_id = state[b'query_id']
    query_data = state[b'query_data']
    stake_amount = state[b'stake_amount']
    governance = encoding.encode_address(state[b'governance_address'])
    num_reports = state[b'num_reports']

    print("---contract variables set on app creation---")
    print("tipper address (the data requester): ", tipper)
    print("query id (unique indicator of data requested): ", query_id)
    print("query data (in depth descriptor of the query id)", query_data)
    print("stake amount in ALGO to become the data reporter: ", stake_amount)
    print("number of values reported: ", num_reports)
    print("governance address: ", governance)
    print("reporter address set later!")

    print("---------------")

    print("staking...")
    #reporter stakes
    scripts.stake()
    print("now staked!")

    state = getAppGlobalState(client, appID=app_id)
    reporter = encoding.encode_address(state[b'reporter_address'])
    staking_status = state[b'staking_status']
    print("data reporter address: ", reporter)
    print("staking status (1 if staked, 0 if not staked): ", staking_status)

    #reporter submits good value
    query_id = b"btc/usd"
    value = b"$40,000"

    scripts.report(query_id=query_id, value=value)
    print("I'm reporting ",query_id, " at ", value)

    #reporter submits bad value
    bad_value = b"$42"
    scripts.report(query_id=query_id, value=bad_value)
    print("I'm a bad actor and I'm reporting ", query_id, " at", bad_value)

    #governance takes away submission privileges from reporter
    print("governance takes away my stake and right to report")
    scripts.vote(0)

    #another reporter reopens feed
    scripts.reporter = getTemporaryAccount()
    scripts.stake()

    state = getAppGlobalState(client, appID=app_id)
    reporter = encoding.decode_address(state[b'reporter_address'])
    print("new reporter address: ", reporter)


    scripts.report(query_id=query_id, value=value)