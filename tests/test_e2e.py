from time import time

import pytest
from algosdk import encoding
from algosdk.algod import AlgodClient
from algosdk.error import AlgodHTTPError
from algosdk.future import transaction
from algosdk.logic import get_application_address

from conftest import App
from scripts.scripts import Scripts
from src.scripts.scripts import Scripts
from src.utils.accounts import Accounts
from src.utils.testing.resources import getTemporaryAccount
from src.utils.util import getAppGlobalState


def test_not_staked_report_attempt(client: AlgodClient, scripts: Scripts, accounts: Accounts, deployed_contract: App):
    """Accounts should not be permitted to report
    if they have not send a stake to the contract"""

    state = getAppGlobalState(client, scripts.feed_app_id)

    assert state[b"staking_status"] == 0
    assert state[b"reporter_address"] == b""


def test_withdraw_before_request(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Reporter cannot withdraw stake without requesting to withdraw"""

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)
    scripts.stake()
    with pytest.raises(AlgodHTTPError):
        scripts.withdraw()


def test_withdraw_after_request_withdraw(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Reporter cannot withdraw stake after initiating withdrawal before waiting 7days"""

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)
    scripts.stake()
    scripts.request_withdraw()

    state = getAppGlobalState(client, feed_id)

    assert state[b"staking_status"] == 2
    assert state[b"reporter_address"] == encoding.decode_address(accounts.reporter.getAddress())
    with pytest.raises(AlgodHTTPError):
        scripts.withdraw()


def test_report_after_request_withdraw(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """reporter can't report after requesting to withdraw"""

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)
    scripts.stake()
    scripts.request_withdraw()
    query_id = "1"
    value = 3500
    timestamp = int(time())
    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id, value, timestamp)


def test_median_computation(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Medianizer -- deploy 5 feeds, submit to 5 feeds, ensure median from
    contract matches median calculated from APIs"""

    value = 3500
    timestamp = int(time())
    median_time = timestamp + 20
    median = 3600
    for i in deployed_contract.feed_ids:
        scripts.feed_app_id = i
        feed_id = scripts.feed_app_id
        scripts.feed_app_address = get_application_address(feed_id)
        scripts.stake()
        query_id = "1"
        scripts.report(query_id, value, timestamp)
        value += 50
        timestamp += 10
        state = getAppGlobalState(client, deployed_contract.medianizer_id)

    state = getAppGlobalState(client, deployed_contract.medianizer_id)

    assert state[b"median"] == median
    assert state[b"median_timestamp"] == median_time


def test_median_update(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """If the median is updated, the timestamp of median is the
    timestamp of the API call"""

    value = 3500
    timestamp = int(time())
    timestamps = []
    for i in range(3):
        scripts.feed_app_id = deployed_contract.feed_ids[i]
        feed_id = scripts.feed_app_id
        scripts.feed_app_address = get_application_address(feed_id)
        scripts.stake()
        query_id = "1"
        scripts.report(query_id, value, timestamp)
        timestamps.append(timestamp)
        value += 50
        timestamp += 10
        state = getAppGlobalState(client, deployed_contract.medianizer_id)

    state = getAppGlobalState(client, deployed_contract.medianizer_id)

    assert state[b"median_timestamp"] == pytest.approx(timestamps[1], 200)


def test_2_feeds(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Medianizer -- ensure that medianizer functions
    with less than 5 feeds"""

    value = 3500
    timestamp = int(time())
    median = (3500 + 3550) / 2
    for i in range(2):
        scripts.feed_app_id = deployed_contract.feed_ids[i]
        feed_id = scripts.feed_app_id
        scripts.feed_app_address = get_application_address(feed_id)
        scripts.stake()
        query_id = "1"
        scripts.report(query_id, value, timestamp)
        value += 50
        timestamp += 10
        state = getAppGlobalState(client, deployed_contract.medianizer_id)

    state = getAppGlobalState(client, deployed_contract.medianizer_id)

    assert state[b"median"] == median
    assert state[b"median_timestamp"] == pytest.approx(time(), 200)


def test_old_timestamp(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Timestamp older than an hour should be rejected"""

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)
    scripts.stake()
    query_id = "1"
    value = 3500
    timestamp = int(time() - 3610)
    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id, value, timestamp)


def test_not_staked_report_attempt(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Accounts should not be permitted to report
    if they have not send a stake to the contract"""

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 0
    assert state[b"reporter_address"] == b""

    query_id = "1"
    value = 3500
    timestamp = int(time())

    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id, value, timestamp)  # expect failure/reversion


def test_report_wrong_query_id(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Reporter should not be able to report to the wrong
    query_id. the transaction should revert if they pass in
    to report() a different query_id"""
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    scripts.stake()

    state = getAppGlobalState(client, scripts.feed_app_id)
    assert state[b"num_reports"] == 0
    state = getAppGlobalState(client, deployed_contract.feed_id)
    assert state[b"staking_status"] == 1
    assert state[b"query_id"] == b"1"

    query_id = b"2"
    value = 3500
    timestamp = int(time() - 1000)
    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id, value, timestamp)


def test_stake_amount(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Reporter should only be able to stake
    with the amount set in the contract"""
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    state = getAppGlobalState(client, deployed_contract.feed_id)
    stake_amount = state[b"stake_amount"]

    # higher stake amount than allowed
    with pytest.raises(AlgodHTTPError):
        scripts.stake(stake_amount=stake_amount + 10)

    # lower stake amount than allowed
    with pytest.raises(AlgodHTTPError):
        scripts.stake(stake_amount=stake_amount - 10)


def test_reporter_double_stake(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """An account shouln't be able to stake twice"""
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    scripts.stake()

    state = getAppGlobalState(client, feed_id)
    assert state[b"staking_status"] == 1  # if 1, account is now staked

    with pytest.raises(AlgodHTTPError):
        scripts.stake()


def test_only_one_staker(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """An account can't replace another account as the reporter
    in other words, a second account
    can't stake if another account is staked"""
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    scripts.stake()

    state = getAppGlobalState(client, feed_id)
    assert state[b"reporter_address"] == encoding.decode_address(accounts.reporter.getAddress())

    scripts.reporter = accounts.bad_actor

    with pytest.raises(AlgodHTTPError):
        scripts.stake()


def test_reporting_without_staking(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Can't report if not staked"""
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    state = getAppGlobalState(client, deployed_contract.feed_id)
    assert state[b"staking_status"] == 0
    assert state[b"query_id"] == b"1"

    query_id = state[b"query_id"]
    value = 3500
    timestamp = int(time() - 1000)
    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id, value, timestamp)


def test_early_withdraw_attempt(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Shouldn't be able to withdraw stake from contract before the 7 day interval"""
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    scripts.stake()
    state = getAppGlobalState(client, feed_id)
    assert state[b"staking_status"] == 1

    scripts.request_withdraw()

    res = scripts.withdraw_dry(timestamp=int(time()) + 518400)  # 6 days in seconds

    assert res["txns"][0]["app-call-messages"][1] == "REJECT"

    scripts.stake()
    scripts.withdraw()
    state = getAppGlobalState(client, scripts.feed_app_id)


# def test_second_withdraw_attempt(scripts: Scripts, accounts: Accounts, deployed_contract, client):
#     """Shouldn't be able to withdraw stake from contract more than once"""
#     scripts.feed_app_id = deployed_contract.feed_ids[0]
#     feed_id = scripts.feed_app_id
#     scripts.feed_app_address = get_application_address(feed_id)

#     scripts.stake()
#     state = getAppGlobalState(client, deployed_contract.feed_id)
#     assert state[b"staking_status"] == 1

#     scripts.request_withdraw()

#     txn = transaction.ApplicationNoOpTxn(
#             sender=accounts.reporter.getAddress(),
#             index=feed_id,
#             app_args=[b"withdraw"],
#             sp=client.suggested_params(),
#         )
#     signedTxn = txn.sign(accounts.reporter.getPrivateKey())
#     res = scripts.withdraw_dry(txns=signedTxn, timestamp=int(time())+604800)

#     with pytest.raises(AlgodHTTPError):
#         scripts.withdraw()


# def test_staking_after_withdrawing(scripts, client, deployed_contract):
#     """contract needs to be redeployed to be open for staking again"""
#     scripts.stake()
#     state = getAppGlobalState(client, deployed_contract.id)
#     assert state[b"staking_status"] == 1

#     scripts.withdraw()
#     with pytest.raises(AlgodHTTPError):
#         scripts.stake()


# def test_reporting_after_withdrawing(scripts, client, deployed_contract):
#     """Reporter can't report once stake has been withdrawn"""

#     scripts.stake()
#     scripts.withdraw()
#     state = getAppGlobalState(client, deployed_contract.id)

#     assert state[b"staking_status"] == 0
#     query_id = b"1"
#     value = b"the data I put on-chain 1234"
#     with pytest.raises(AlgodHTTPError):
#         scripts.report(query_id, value)


def test_request_withdraw_without_staking(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Shouldn't be able to request a withdraw without staking"""
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 0
    assert state[b"reporter_address"] == b""

    with pytest.raises(AlgodHTTPError):
        scripts.request_withdraw()


def test_withdraw_after_slashing(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Reporter shouldn't be able to withdraw stake after being slashed"""
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    scripts.stake()
    state = getAppGlobalState(client, feed_id)
    assert state[b"staking_status"] == 1
    scripts.slash_reporter(multisigaccounts_sk=accounts.multisig_signers_sk)  # 0 means reporter slashed

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 0

    with pytest.raises(AlgodHTTPError):
        scripts.request_withdraw()


def test_overflow_in_create(scripts: Scripts, accounts: Accounts, deployed_contract, client):
    """Contract deployment should revert if
    bytes inputs are longer than 128 bytes"""

    too_long_query_id = "a" * 129
    query_data = "my query_id is invalid because it is >128 bytes in length"

    with pytest.raises(AlgodHTTPError):
        scripts.deploy_tellor_flex(
            query_id=too_long_query_id,
            query_data=query_data,
            timestamp_freshness=3600,
            multisigaccounts_sk=accounts.multisig_signers_sk,
        )
