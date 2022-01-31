from copyreg import constructor
from curses import qiflush
from http import client
from pydoc import cli
from time import time, sleep

import pytest

from algosdk import account, encoding
from algosdk.logic import get_application_address

from tellorflex.methods import create, stake, vote, report, withdraw
from scripts.deploy import Scripts
from utils.helpers import _algod_client
from testing.setup import getAlgodClient
from utils.util import  getBalances, getAppGlobalState, getLastBlockTimestamp
from testing.resources import getTemporaryAccount, optInToAsset, createDummyAsset
from utils.helpers import call_sandbox_command
from utils.helpers import add_standalone_account

def test_create():
    client = getAlgodClient()

    tipper = getTemporaryAccount(client)
    _, reporter_addr = account.generate_account()
    _, governance_addr = account.generate_account()

    construct = Scripts(client=client,
                        tipper=tipper,
                        reporter=reporter_addr,
                        governance_address=governance_addr
                        )

    query_id = b'hi'
    query_data = b'hi'

    appID = construct.deploy_tellor_flex(
        query_id=query_id,
        query_data=query_data
    )
    
    actual = getAppGlobalState(client, appID)
    expected = {
        b'governance_address': encoding.decode_address(governance_addr),
        b'query_id': query_id,
        b'query_data': query_data,
        b'num_reports': 0,
        b'stake_amount': 180*1000000,
        b'staking_status': 0,
        b'tipper': encoding.decode_address(tipper.getAddress())
    }

    assert actual == expected

def stake():
    # reporter address is; reporter = getTemporaryAccount(client)
    # 
    pass