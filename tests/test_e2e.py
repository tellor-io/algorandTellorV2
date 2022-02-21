import pytest
from algosdk import encoding
from algosdk.error import AlgodHTTPError

from utils.testing.resources import getTemporaryAccount
from utils.util import getAppGlobalState


def test_not_staked_report_attempt(scripts, accounts, deployed_contract):
    """Accounts should not be permitted to report
    if they have not send a stake to the contract"""

    assert deployed_contract.state[b"staking_status"] == 0
    assert deployed_contract.state[b"reporter_address"] == b""

    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id=b"1", value=b"the data I put on-chain 1234")  # expect failure/reversion


def test_report_wrong_query_id(client, scripts, deployed_contract):
    """Reporter should not be able to report to the wrong
    query_id. the transaction should revert if they pass in
    to report() a different query_id than the one specified
    in the contract by the tipper"""

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"num_reports"] == 0
    assert state[b"query_id"] == b"1"

    query_id = b"2"
    value = b"the data I put on-chain 1234"
    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id, value)


def test_stake_amount(client, scripts, deployed_contract):
    """Reporter should only be able to stake
    with the amount set in the contract by the tipper"""

    state = getAppGlobalState(client, deployed_contract.id)
    stake_amount = state[b"stake_amount"]

    # higher stake amount than allowed
    with pytest.raises(AlgodHTTPError):
        scripts.stake(stake_amount=stake_amount + 10)

    # lower stake amount than allowed
    with pytest.raises(AlgodHTTPError):
        scripts.stake(stake_amount=stake_amount - 10)


def test_reporter_double_stake(client, scripts, deployed_contract):
    """An account shouln't be able to stake twice"""

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"staking_status"] == 1  # if 1, account is now staked

    with pytest.raises(AlgodHTTPError):
        scripts.stake()


def test_only_one_staker(client, accounts, scripts, deployed_contract):
    """An account can't replace another account as the reporter
    in other words, a second account
    can't stake if another account is staked"""

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"reporter_address"] == encoding.decode_address(accounts.reporter.getAddress())

    scripts.reporter = getTemporaryAccount(client)

    with pytest.raises(AlgodHTTPError):
        scripts.stake()


def test_second_withdraw_attempt(scripts, client, deployed_contract):
    """Shouldn't be able to withdraw stake from contract more than once"""
    scripts.stake()
    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"staking_status"] == 1

    scripts.withdraw()

    with pytest.raises(AlgodHTTPError):
        scripts.withdraw()


def test_staking_after_withdrawing(scripts, client, deployed_contract):
    """contract needs to be redeployed to be open for staking again"""
    scripts.stake()
    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"staking_status"] == 1

    scripts.withdraw()
    with pytest.raises(AlgodHTTPError):
        scripts.stake()


def test_reporting_after_withdrawing(scripts, client, deployed_contract):
    """Reporter can't report once stake has been withdrawn"""

    scripts.stake()
    scripts.withdraw()
    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b"staking_status"] == 0
    query_id = b"1"
    value = b"the data I put on-chain 1234"
    with pytest.raises(AlgodHTTPError):
        scripts.report(query_id, value)


def test_withdrawing_without_staking(scripts, deployed_contract):
    """Shouldn't be able to withdraw without staking"""
    assert deployed_contract.state[b"staking_status"] == 0
    assert deployed_contract.state[b"reporter_address"] == b""

    with pytest.raises(AlgodHTTPError):
        scripts.withdraw()


def test_wrong_vote_input(scripts):
    """checks other vote input other than 0 and 1"""
    with pytest.raises(AlgodHTTPError):
        scripts.vote(5)


def test_withdraw_after_slashing(scripts, client, deployed_contract):
    """Reporter shouldn't be able to withdraw stake after being slashed"""
    scripts.stake()
    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"staking_status"] == 1
    scripts.vote(0)  # 0 means reporter slashed

    with pytest.raises(AlgodHTTPError):
        scripts.withdraw()


def test_overflow_in_create(scripts, client):
    """Contract deployment should revert if
    bytes inputs are longer than 128 bytes"""

    too_long_query_id = "a" * 129
    query_data = "my query_id is invalid because it is >128 bytes in length"

    with pytest.raises(AlgodHTTPError):
        scripts.deploy_tellor_flex(query_id=too_long_query_id, query_data=query_data)
