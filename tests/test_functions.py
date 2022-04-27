from time import time

import pytest
from algosdk import constants
from algosdk import encoding
from algosdk.algod import AlgodClient
from algosdk.error import AlgodHTTPError
from algosdk.future import transaction
from algosdk.logic import get_application_address

from conftest import App
from src.scripts.scripts import Scripts
from src.utils.accounts import Accounts
from src.utils.testing.resources import getTemporaryAccount
from src.utils.util import getAppGlobalState
from src.utils.util import waitForTransaction


def test_activate_contract(client: AlgodClient, accounts: Accounts, deployed_contract: App):
    """
    Test activate_contract method on medianizer_contract
    """

    medianzier_state = getAppGlobalState(client, deployed_contract.medianizer_id)
    n = 1
    for i in deployed_contract.feed_ids:
        feed_state = getAppGlobalState(client, i)
        app = "app_" + f"{n}"
        encoded = app.encode("utf-8")
        addr = get_application_address(i)
        n += 1
        assert medianzier_state[encoded] == encoding.decode_address(addr)
        assert feed_state[b"medianizer"] == deployed_contract.medianizer_id

    assert medianzier_state[b"governance"] == encoding.decode_address(accounts.governance.address())


def test_change_governance(client: AlgodClient, accounts: Accounts, deployed_contract: App):
    """
    Test change_governance method on feed
    """
    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    old_gov_address = state[b"governance_address"]
    new_gov_address = getTemporaryAccount(client).getAddress()
    assert old_gov_address == encoding.decode_address(accounts.governance.address())

    # require 1: should revert if not called by current governance address
    with pytest.raises(AlgodHTTPError):

        txn = transaction.ApplicationNoOpTxn(
            sender=accounts.bad_actor.getAddress(),
            app_args=["change_governance", encoding.decode_address(new_gov_address)],
            sp=client.suggested_params(),
            index=deployed_contract.feed_ids[0],
        )

        signedTxn = txn.sign(accounts.bad_actor.getPrivateKey())
        client.send_transaction(signedTxn)
        waitForTransaction(client, signedTxn.get_txid(), timeout=30)


def test_change_governance_medianizer(client: AlgodClient, accounts: Accounts, deployed_contract: App):
    """
    Test change_governance method on medianizer
    """
    state = getAppGlobalState(client, deployed_contract.medianizer_id)
    old_gov_address = state[b"governance"]
    new_gov_address = getTemporaryAccount(client).getAddress()
    assert old_gov_address == encoding.decode_address(accounts.governance.address())

    # require 1: should revert if not called by current governance address
    with pytest.raises(AlgodHTTPError):

        txn = transaction.ApplicationNoOpTxn(
            sender=accounts.bad_actor.getAddress(),
            app_args=["change_governance", encoding.decode_address(new_gov_address)],
            sp=client.suggested_params(),
            index=deployed_contract.medianizer_id,
        )

        signedTxn = txn.sign(accounts.bad_actor.getPrivateKey())
        client.send_transaction(signedTxn)
        waitForTransaction(client, signedTxn.get_txid(), timeout=30)

    # require 2: should revert if no new governance address is submitted
    with pytest.raises(AlgodHTTPError):
        txn = transaction.ApplicationNoOpTxn(
            sender=accounts.governance.address(),
            app_args=["change_governance", ""],
            sp=client.suggested_params(),
            index=deployed_contract.medianizer_id,
        )

        mtx = transaction.MultisigTransaction(txn, accounts.governance)
        for i in accounts.multisig_signers_sk:
            mtx.sign(i)

        txid = client.send_raw_transaction(encoding.msgpack_encode(mtx))
        transaction.wait_for_confirmation(client, txid, 6)

    # assert governance should be a different address
    txn = transaction.ApplicationNoOpTxn(
        sender=accounts.governance.address(),
        app_args=["change_governance", encoding.decode_address(new_gov_address)],
        sp=client.suggested_params(),
        index=deployed_contract.medianizer_id,
    )

    mtx = transaction.MultisigTransaction(txn, accounts.governance)
    for i in accounts.multisig_signers_sk:
        mtx.sign(i)
    txid = client.send_raw_transaction(encoding.msgpack_encode(mtx))
    state = getAppGlobalState(client, deployed_contract.medianizer_id)
    assert state[b"governance"] == encoding.decode_address(new_gov_address)


def test_change_medianizer(client: AlgodClient, accounts: Accounts, deployed_contract: App):
    """
    Test change medianzier id on feed
    """
    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    old_medianizer_id = state[b"medianizer"]
    assert old_medianizer_id == deployed_contract.medianizer_id

    new_medianizer_id = 1234

    # require 1: should revert if not called by current governance address
    with pytest.raises(AlgodHTTPError):
        txn = transaction.ApplicationNoOpTxn(
            accounts.bad_actor.getAddress(),
            client.suggested_params(),
            app_args=["change_medianizer", new_medianizer_id],
            index=deployed_contract.feed_ids[0],
        )

        signedTxn = txn.sign(accounts.bad_actor.getPrivateKey())
        client.send_transaction(signedTxn)
        waitForTransaction(client, signedTxn.get_txid(), timeout=30)


def test_get_values(client: AlgodClient, scripts: Scripts, accounts: Accounts, deployed_contract: App):
    """
    Test get_values() method on medianizer_contract
    """
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    feed_state = getAppGlobalState(client, feed_id)
    assert feed_state[b"reporter_address"] == b""

    scripts.tip(300000)
    scripts.stake()

    feed_state = getAppGlobalState(client, feed_id)
    assert feed_state[b"staking_status"] == 1
    assert feed_state[b"reporter_address"] == encoding.decode_address(accounts.reporter.getAddress())

    query_id = b"1"
    value = 3500
    timestamp = int(time() - 500)

    scripts.report(query_id, value, timestamp)

    medianizer_state = getAppGlobalState(client, deployed_contract.medianizer_id)

    assert feed_state[b"query_id"] == query_id
    assert medianizer_state[b"median"] == value
    assert medianizer_state[b"median_timestamp"] == timestamp


def test_report(client: AlgodClient, scripts: Scripts, accounts: Accounts, deployed_contract: App):
    """
    Test report() method on contract
    """
    tip = 100000
    for i in deployed_contract.feed_ids:
        scripts.feed_app_id = i
        feed_id = scripts.feed_app_id
        scripts.feed_app_address = get_application_address(feed_id)

        scripts.tip(tip)
        scripts.stake()

        state = getAppGlobalState(client, i)
        assert state[b"reporter_address"] == encoding.decode_address(accounts.reporter.getAddress())
        assert state[b"staking_status"] == 1

        query_id = b"1"
        value = 3450
        timestamp = int(time() - 1000)
        reporter_balance_before = client.account_info(accounts.reporter.getAddress()).get("amount")

        assert state[b"tip_amount"] == tip
        governance_balance_before = client.account_info(accounts.governance.address()).get("amount")
        scripts.report(query_id, value, timestamp)

        state = getAppGlobalState(client, i)
        reporter_balance_after = client.account_info(accounts.reporter.getAddress()).get("amount")
        governance_balance_after = client.account_info(accounts.governance.address()).get("amount")

        encoded = int.to_bytes(timestamp, length=8, byteorder="big") + int.to_bytes(value, length=8, byteorder="big")
        assert state[b"last_value"] == encoded
        assert reporter_balance_after == (reporter_balance_before + int(tip * 0.98)) - (constants.MIN_TXN_FEE)
        assert governance_balance_after == (governance_balance_before + (tip * 0.02))
        assert state[b"tip_amount"] == 0


def test_request_withdraw(client: AlgodClient, scripts: Scripts, deployed_contract: App):
    """
    Test request_withdraw() method on feed contract
    """
    # set feed id for app to test request_withdraw()
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id

    # set feed app address
    scripts.feed_app_address = get_application_address(feed_id)

    # stake reporter
    scripts.stake()

    # get state of feed app after staking reporter
    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    # assert staking status before fn call is 1
    assert state[b"staking_status"] == 1

    # assert lock_timestamp is 0
    assert state[b"lock_timestamp"] == 0

    # call request_withdraw
    scripts.request_withdraw()

    # get state again
    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    # assert stake timestamp is now approx. time.time()
    assert state[b"lock_timestamp"] == pytest.approx(int(time()), 500)

    # assert staking status is now 2
    assert state[b"staking_status"] == 2

    # require 3: assert reporter cant request withdrawal while in state 2
    with pytest.raises(AlgodHTTPError):
        scripts.request_withdraw()


def test_slash_reporter(client: AlgodClient, scripts: Scripts, accounts: Accounts, deployed_contract: App):
    """
    Test slash_reporter() method on contract
    """
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id
    scripts.feed_app_address = get_application_address(feed_id)

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    assert state[b"staking_status"] == 1
    governance_algo_balance_before = client.account_info(accounts.governance.address()).get("amount")

    scripts.slash_reporter(multisigaccounts_sk=accounts.multisig_signers_sk)

    governance_algo_balance_after = client.account_info(accounts.governance.address()).get("amount")
    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 0
    assert state[b"reporter_address"] == b""
    assert governance_algo_balance_after == governance_algo_balance_before + state[b"stake_amount"] - (
        2 * constants.MIN_TXN_FEE
    )


def test_stake(client: AlgodClient, scripts: Scripts, accounts: Accounts, deployed_contract: App):
    """
    Test stake() method on contract
    """
    client.suggested_params().flatFee = True
    client.suggested_params().fee = 2 * constants.MIN_TXN_FEE
    stake_amount = 200000
    for i in deployed_contract.feed_ids:
        scripts.feed_app_id = i
        feed_id = scripts.feed_app_id
        scripts.feed_app_address = get_application_address(feed_id)

        reporter_algo_balance_before = client.account_info(accounts.reporter.getAddress()).get("amount")
        state = getAppGlobalState(client, i)

        assert state[b"staking_status"] == 0
        assert state[b"reporter_address"] == b""

        scripts.stake()

        state = getAppGlobalState(client, i)

        assert state[b"staking_status"] == 1
        assert state[b"reporter_address"] == encoding.decode_address(accounts.reporter.getAddress())

        reporter_algo_balance_after = client.account_info(accounts.reporter.getAddress()).get("amount")
        assert reporter_algo_balance_after == reporter_algo_balance_before - stake_amount - (2 * constants.MIN_TXN_FEE)


def test_tip(client: AlgodClient, scripts: Scripts, accounts: Accounts, deployed_contract: App):
    """
    Test tip() method on feed contract
    """

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    scripts.feed_app_address = get_application_address(scripts.feed_app_id)

    tip_amount = 400000
    suggestedParams = scripts.client.suggested_params()

    # require 1: revert if group tx senders are not the same account

    with pytest.raises(AlgodHTTPError):
        payTxn = transaction.PaymentTxn(
            sender=accounts.bad_actor.getAddress(),
            receiver=scripts.feed_app_address,
            amt=tip_amount,
            sp=suggestedParams,
        )

        no_op_txn = transaction.ApplicationNoOpTxn(
            sender=scripts.tipper.getAddress(),
            index=deployed_contract.feed_ids[0],
            app_args=[b"tip"],
            sp=suggestedParams,
        )

        signed_pay_txn = payTxn.sign(scripts.tipper.getPrivateKey())
        signed_no_op_txn = no_op_txn.sign(scripts.tipper.getPrivateKey())

        client.send_transactions([signed_pay_txn, signed_no_op_txn])

        waitForTransaction(client, no_op_txn.get_txid())

    # require 2: revert if txn 1 in group txn
    # does not transfer algo to the feed contract

    with pytest.raises(AlgodHTTPError):
        payTxn = transaction.PaymentTxn(
            sender=accounts.bad_actor.getAddress(),
            receiver=accounts.tipper.getAddress(),
            amt=tip_amount,
            sp=suggestedParams,
        )

        no_op_txn = transaction.ApplicationNoOpTxn(
            sender=scripts.tipper.getAddress(),
            index=deployed_contract.feed_ids[0],
            app_args=[b"tip"],
            sp=suggestedParams,
        )

        signed_pay_txn = payTxn.sign(scripts.tipper.getPrivateKey())
        signed_no_op_txn = no_op_txn.sign(scripts.tipper.getPrivateKey())

        client.send_transactions([signed_pay_txn, signed_no_op_txn])

        waitForTransaction(client, no_op_txn.get_txid())

    # require 3: revert if txn 1 is not a payment tx
    with pytest.raises(AlgodHTTPError):
        payTxn = transaction.ApplicationNoOpTxn(
            sender=accounts.bad_actor.getAddress(),
            index=deployed_contract.feed_ids[0],
            app_args=[b"report"],
            sp=suggestedParams,
        )

        no_op_txn = transaction.ApplicationNoOpTxn(
            sender=scripts.tipper.getAddress(),
            index=deployed_contract.feed_ids[0],
            app_args=[b"tip"],
            sp=suggestedParams,
        )

        signed_pay_txn = payTxn.sign(scripts.tipper.getPrivateKey())
        signed_no_op_txn = no_op_txn.sign(scripts.tipper.getPrivateKey())

        client.send_transactions([signed_pay_txn, signed_no_op_txn])

        waitForTransaction(client, no_op_txn.get_txid())

    # assert that tx will revert if not grouped

    with pytest.raises(AlgodHTTPError):

        no_op_txn = transaction.ApplicationNoOpTxn(
            sender=scripts.tipper.getAddress(),
            index=deployed_contract.feed_ids[0],
            app_args=[b"tip"],
            sp=suggestedParams,
        )

        signed_no_op_txn = no_op_txn.sign(scripts.tipper.getPrivateKey())

        client.send_transactions([signed_no_op_txn])

        waitForTransaction(client, no_op_txn.get_txid())

    # assert that the tip_amount state variable is equal to
    # the algo transferred in txn 1

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    prev_tip_amount = state[b"tip_amount"]

    scripts.tip(tip_amount)

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    curr_tip_amount = state[b"tip_amount"]

    assert curr_tip_amount == prev_tip_amount + tip_amount


def test_withdraw(client: AlgodClient, scripts: Scripts, deployed_contract: App):
    """
    Test withdraw() method on contract
    """
    #   set feed id for app to test withdraw()
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    feed_id = scripts.feed_app_id

    # set feed app address
    scripts.feed_app_address = get_application_address(feed_id)

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 0

    # stake reporter
    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 1

    scripts.request_withdraw()

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    # assert staking status changed to 2 meaning withdrawal requested
    assert state[b"staking_status"] == 2

    # dryrun withdrawal after 1 day
    res = scripts.withdraw_dry(timestamp=int(time()) + 86401)

    assert encoding.base64.b64encode(b"staking_status").decode("utf-8") == res["txns"][0]["global-delta"][0]["key"]
    assert res["txns"][0]["global-delta"][0]["value"]["uint"] == 0
    assert encoding.base64.b64encode(b"lock_timestamp").decode("utf-8") == res["txns"][0]["global-delta"][1]["key"]
    assert res["txns"][0]["global-delta"][1]["value"]["uint"] == 0
