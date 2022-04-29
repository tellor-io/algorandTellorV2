from time import time

import pytest
from algosdk import constants
from algosdk import encoding
from algosdk.algod import AlgodClient
from algosdk.error import AlgodHTTPError
from algosdk.logic import get_application_address

from conftest import App
from src.scripts.scripts import Scripts
from src.utils.accounts import Accounts
from src.utils.util import getAppGlobalState


def test_2_feeds(scripts: Scripts, deployed_contract: App, client: AlgodClient):
    """
    Medianizer -- ensure that medianizer functions
    with less than 5 feeds
    """

    value = 3500
    timestamp = int(time() - 500)
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


def test_accuracy_bytes_slicing(scripts: Scripts, deployed_contract: App, client: AlgodClient):
    """
    After a report is submitted, the `last_value` global var
    should contain an accurate value and timestamp
    """

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    scripts.stake()

    query_id = b"1"
    value = 40000
    timestamp = int(time() - 500)

    scripts.report(query_id, value, timestamp)

    state = getAppGlobalState(client, feed_id)

    last_value_and_timestamp = state[b"last_value"]

    assert len(last_value_and_timestamp) == 16

    on_chain_timestamp = last_value_and_timestamp[:8]
    on_chain_value = last_value_and_timestamp[8:]

    assert int.from_bytes(on_chain_value, "big") == value
    assert int.from_bytes(on_chain_timestamp, "big") == timestamp


def test_early_withdraw_attempt(scripts: Scripts, deployed_contract: App, client: AlgodClient):
    """
    Shouldn't be able to withdraw stake from contract
    before the 1 day interval
    """
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    scripts.stake()
    state = getAppGlobalState(client, feed_id)
    assert state[b"staking_status"] == 1

    scripts.request_withdraw()

    res = scripts.withdraw_dry(timestamp=int(time()) + 86000)  # 1 day minus 400 seconds

    assert res["txns"][0]["app-call-messages"][1] == "REJECT"


def test_median_computation(scripts: Scripts, deployed_contract: App, client: AlgodClient):
    """
    Medianizer -- deploy 5 feeds, submit to 5 feeds,
    ensure median from contract matches median calculated from APIs
    """

    value = 3500
    timestamp = int(time() - 500)
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


def test_median_update(scripts: Scripts, deployed_contract: App, client: AlgodClient):
    """
    If the median is updated, the timestamp of median is the
    timestamp of the API call
    """

    value = 3500
    timestamp = int(time() - 500)
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


def test_not_staked_report_attempt(scripts: Scripts, deployed_contract: App, client: AlgodClient):
    """
    Accounts should not be permitted to report
    if they have not send a stake to the contract
    """

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 0
    assert state[b"reporter_address"] == b""

    query_id = "1"
    value = 3500
    timestamp = int(time())

    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id, value, timestamp)  # expect failure/reversion


def test_old_timestamp(scripts: Scripts, deployed_contract: App):
    """
    Timestamp older than an hour should be rejected
    """

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)
    scripts.stake()
    query_id = "1"
    value = 3500
    timestamp = int(time() - 3610)
    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id, value, timestamp)


def test_only_one_staker(scripts: Scripts, accounts: Accounts, deployed_contract: App, client: AlgodClient):
    """
    An account can't replace another account as the reporter
    in other words, a second account
    can't stake if another account is staked
    """
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    scripts.stake()

    state = getAppGlobalState(client, feed_id)
    assert state[b"reporter_address"] == encoding.decode_address(accounts.reporter.getAddress())

    scripts.reporter = accounts.bad_actor

    with pytest.raises(AlgodHTTPError):
        scripts.stake()


def test_overflow_in_create(scripts: Scripts, accounts: Accounts):
    """
    Contract deployment should revert if
    bytes inputs are longer than 128 bytes
    """

    too_long_query_id = "a" * 129
    query_data = "my query_id is invalid because it is >128 bytes in length"

    with pytest.raises(AlgodHTTPError):
        scripts.deploy_tellor_flex(
            query_id=too_long_query_id,
            query_data=query_data,
            timestamp_freshness=3600,
            multisigaccounts_sk=accounts.multisig_signers_sk,
        )


def test_report_after_request_withdraw(scripts: Scripts, deployed_contract: App):
    """
    reporter can't report after requesting to withdraw
    """

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


def test_report_wrong_query_id(scripts: Scripts, deployed_contract: App, client: AlgodClient):
    """
    Reporter should not be able to report to the wrong
    query_id. the transaction should revert if they pass in
    to report() a different query_id
    """
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    scripts.stake()

    state = getAppGlobalState(client, feed_id)
    assert state[b"staking_status"] == 1
    assert state[b"query_id"] == b"1"

    query_id = b"2"
    value = 3500
    timestamp = int(time() - 1000)
    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id, value, timestamp)


def test_reporting_after_requesting_withdraw(scripts: Scripts, deployed_contract: App, client: AlgodClient):
    """
    Reporter can't report once withdraw requested
    """

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    scripts.stake()

    scripts.request_withdraw()
    state = getAppGlobalState(client, feed_id)

    assert state[b"staking_status"] == 2
    query_id = b"1"
    value = b"the data I put on-chain 1234"
    timestamp = int(time() - 1000)
    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id, value, timestamp)


def test_reporting_without_staking(scripts: Scripts, deployed_contract: App, client: AlgodClient):
    """
    Can't report if not staked
    """
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    state = getAppGlobalState(client, feed_id)
    assert state[b"staking_status"] == 0
    assert state[b"query_id"] == b"1"

    query_id = state[b"query_id"]
    value = 3500
    timestamp = int(time() - 1000)
    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id, value, timestamp)


def test_reporter_clearing_algo_from_contract(scripts: Scripts, deployed_contract: App, client: AlgodClient):
    """
    Reporter shouldn't empty contract of all ALGO on claiming a tip
    """

    tip_amt = 300000

    # get app id and app address
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)
    app_address = scripts.feed_app_address

    # get app balance before any staking
    app_balance_b4_staking = client.account_info(app_address).get("amount")

    # assert that app doesn't have any balance initially
    assert app_balance_b4_staking == 0

    # add tip to the contract
    scripts.tip(tip_amt)

    # check app balance after a tip has been added
    app_balance_after_tipping = client.account_info(app_address).get("amount")

    # assert app balance is same as tip amount after a tip is added
    assert app_balance_after_tipping == tip_amt

    # reporter adds a stake to the app
    scripts.stake()
    # get state of the after reporter stakes
    state = getAppGlobalState(client, feed_id)
    stake_amt = state[b"stake_amount"]

    # check app balance after reporter adds stake
    app_balance_after_staking = client.account_info(app_address).get("amount")

    # app balance should equal the tip amount plus stake amount
    assert app_balance_after_staking == tip_amt + stake_amt

    query_id = b"1"
    value = 3500
    timestamp = int(time() - 1000)

    # reporter submits value and is tipped instantaneously
    scripts.report(query_id, value, timestamp)

    # get app balance after reporter submits a value
    app_balance_after_report = client.account_info(app_address).get("amount")

    # app balance should be reduced by only the tip amount after reporter takes the tip
    assert app_balance_after_report == pytest.approx((tip_amt + stake_amt - tip_amt - constants.MIN_TXN_FEE * 3), 400)


#
def test_reporter_double_stake(scripts: Scripts, deployed_contract: App, client: AlgodClient):
    """
    An account shouln't be able to stake twice
    """
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    scripts.stake()

    state = getAppGlobalState(client, feed_id)
    assert state[b"staking_status"] == 1  # if 1, account is now staked

    with pytest.raises(AlgodHTTPError):
        scripts.stake()


def test_reporter_tip_receipt(scripts: Scripts, accounts: Accounts, deployed_contract: App, client: AlgodClient):
    """
    Reporter receives correct tip amount after multiple consecutive tips
    """
    tip_amt = 300000

    # get app id and app address
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    # add tip to the contract multiple times
    scripts.tip(tip_amt)
    scripts.tip(tip_amt)
    scripts.tip(tip_amt)

    # reporter adds a stake to the app
    scripts.stake()

    # get reporter balance before any reporting
    reporter_balance_b4_staking = client.account_info(accounts.reporter.getAddress()).get("amount")

    query_id = b"1"
    value = 3500
    timestamp = int(time() - 1000)

    # reporter submits value and is tipped instantaneously
    scripts.report(query_id, value, timestamp)

    # get reporter balance after submiting a value
    reporter_balance_after_report = client.account_info(accounts.reporter.getAddress()).get("amount")

    # reporter balance should increase by 3 times the tip amount minus 2% fee
    tip_amt = (tip_amt * 98) / 100
    assert reporter_balance_after_report == pytest.approx(
        (reporter_balance_b4_staking + (tip_amt * 3) - constants.MIN_TXN_FEE), 400
    )


def test_request_withdraw_without_staking(scripts: Scripts, deployed_contract: App, client: AlgodClient):
    """
    Shouldn't be able to request a withdraw without staking
    """
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 0
    assert state[b"reporter_address"] == b""

    with pytest.raises(AlgodHTTPError):
        scripts.request_withdraw()


def test_stake_amount(scripts: Scripts, deployed_contract: App, client: AlgodClient):
    """
    Reporter should only be able to stake
    with the amount set in the contract
    """
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    state = getAppGlobalState(client, feed_id)
    stake_amount = state[b"stake_amount"]

    # higher stake amount than allowed
    with pytest.raises(AlgodHTTPError):
        scripts.stake(stake_amount=stake_amount + 10)

    # lower stake amount than allowed
    with pytest.raises(AlgodHTTPError):
        scripts.stake(stake_amount=stake_amount - 10)


def test_tip_amount_received_by_reporter(
    scripts: Scripts, accounts: Accounts, deployed_contract: App, client: AlgodClient
):
    """
    Reporter receives correct tip amount on single tip
    """

    tip_amt = 300000
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    # tip added to feed app
    scripts.tip(tip_amt)

    # reporter stakes to become reporter
    scripts.stake()

    # get reporter balance before a report is submitted
    reporter_balance_b4_tipping = client.account_info(accounts.reporter.getAddress()).get("amount")

    query_id = b"1"
    value = 3500
    timestamp = int(time() - 1000)

    # reporter submits a value
    scripts.report(query_id, value, timestamp)

    # get reporter balance after they submit a value
    reporter_balance_after_tipping = client.account_info(accounts.reporter.getAddress()).get("amount")

    # reporter balance should increase to 98 percent of tip amount
    assert reporter_balance_after_tipping == pytest.approx(
        ((reporter_balance_b4_tipping + (tip_amt * 0.98)) - constants.MIN_TXN_FEE), 400
    )


def test_withdraw_after_request_withdraw(
    scripts: Scripts, accounts: Accounts, deployed_contract: App, client: AlgodClient
):
    """
    Reporter cannot withdraw stake after initiating
    withdrawal before waiting a 24hr
    """

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


def test_withdraw_before_request(scripts: Scripts, deployed_contract: App):
    """Reporter cannot withdraw stake without requesting to withdraw"""

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)
    scripts.stake()
    with pytest.raises(AlgodHTTPError):
        scripts.withdraw()


def test_withdraw_after_slashing(scripts: Scripts, accounts: Accounts, deployed_contract: App, client: AlgodClient):
    """
    Reporter shouldn't be able to withdraw stake after being slashed
    """
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
