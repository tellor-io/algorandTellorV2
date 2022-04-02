import time

import pytest
from algosdk import encoding
from algosdk.error import AlgodHTTPError
from algosdk.future import transaction

from src.utils.util import getAppGlobalState, waitForTransaction
from utils.senders import send_no_op_tx
from utils.testing.resources import getTemporaryAccount

def test_change_governance(client, scripts, accounts, deployed_contract):

    state = getAppGlobalState(client, deployed_contract.id)
    old_gov_address = state[b"governance_contract"]
    new_gov_address = getTemporaryAccount(client).addr
    
    #require 1: should revert if not called by current governance address
    with pytest.raises(AlgodHTTPError):
        send_no_op_tx(accounts.bad_actor, scripts.feed_app_id, fn_name="change_governance", app_args=[new_gov_address])

    #require 2: should revert if no new governance address is submitted
    with pytest.raises(AlgodHTTPError):
        send_no_op_tx(accounts.governance, scripts.feed_app_id, fn_name="change_governance")

    send_no_op_tx(accounts.governance, scripts.feed_app_id, fn_name="change_governance", app_args=[new_gov_address])

    #assert governance should be a different address

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"governance_contract"] == new_gov_address


def test_change_medianizer(client, scripts, accounts, deployed_contract):

    state = getAppGlobalState(client, deployed_contract.id)
    old_medianizer_id = state[b"medianizer"]
    new_medianizer_id = 1234
    
    #require 1: should revert if not called by current governance address
    with pytest.raises(AlgodHTTPError):
        send_no_op_tx(accounts.bad_actor, scripts.feed_app_id, fn_name="change_medianizer", foreign_apps=[new_medianizer_id])

    #require 2: should revert if no new governance address is submitted
    with pytest.raises(AlgodHTTPError):
        send_no_op_tx(accounts.governance, scripts.feed_app_id, fn_name="change_medianizer")

    send_no_op_tx(accounts.governance, scripts.feed_app_id, fn_name="change_medianizer", foreign_apps=[new_medianizer_id])

    #assert governance should be a different address

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"medianizer"] == new_medianizer_id
    
def test_report(client, scripts, accounts, deployed_contract):
    """Test report() method on contract"""

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"num_reports"] == 0

    query_id = b"1"
    value = b"the data I put on-chain 1234"
    scripts.report(query_id, value)

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"num_reports"] == 0  # won't increment until approved by governance
    assert state[b"value"] == value
    assert pytest.approx(state[b"timestamp"], 100) == int(time.time())

    new_value = b"a new data value 4567"
    scripts.report(query_id, new_value)

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"num_reports"] == 0  # won't increment until approved by governance
    assert state[b"value"] == new_value
    assert pytest.approx(state[b"timestamp"], 100) == int(time.time())


def test_stake(client, scripts, accounts, deployed_contract):
    """Test stake() method on contract"""

    stake_amount = 200000

    reporter_algo_balance_before = client.account_info(accounts.reporter.getAddress()).get("amount")
    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b"staking_status"] == 0
    assert state[b"reporter_address"] == b""

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b"staking_status"] == 1
    assert state[b"reporter_address"] == encoding.decode_address(accounts.reporter.getAddress())

    reporter_algo_balance_after = client.account_info(accounts.reporter.getAddress()).get("amount")
    assert reporter_algo_balance_after == reporter_algo_balance_before - stake_amount - client.fee * 2


def test_tip(client, scripts, accounts, deployed_contract):
    """Test tip() method on feed contract"""

    tip_amount = 4
    suggestedParams = scripts.client.suggested_params()

    # require 1: revert if group tx senders are not the same account

    with pytest.raises(AlgodHTTPError):
        payTxn = transaction.PaymentTxn(
                sender=accounts.bad_actor.getAddress(), receiver=scripts.app_address, amt=tip_amount, sp=suggestedParams
            )

        no_op_txn = transaction.ApplicationNoOpTxn(
            sender=scripts.tipper.getAddress(), index=scripts.feed_app_id, app_args=[b"tip"], sp=suggestedParams
        )

        signed_pay_txn = payTxn.sign(scripts.tipper.getPrivateKey())
        signed_no_op_txn = no_op_txn.sign(scripts.tipper.getPrivateKey())

        client.send_transactions([signed_pay_txn, signed_no_op_txn])

        waitForTransaction(client, no_op_txn.get_txid())    

    # require 2: revert if txn 1 in group txn 
    # does not transfer algo to the feed contract

    with pytest.raises(AlgodHTTPError):
        payTxn = transaction.PaymentTxn(
                sender=accounts.bad_actor.getAddress(), receiver=accounts.tipper.getAddress(), amt=tip_amount, sp=suggestedParams
            )

        no_op_txn = transaction.ApplicationNoOpTxn(
            sender=scripts.tipper.getAddress(), index=scripts.feed_app_id, app_args=[b"tip"], sp=suggestedParams
        )

        signed_pay_txn = payTxn.sign(scripts.tipper.getPrivateKey())
        signed_no_op_txn = no_op_txn.sign(scripts.tipper.getPrivateKey())

        client.send_transactions([signed_pay_txn, signed_no_op_txn])

        waitForTransaction(client, no_op_txn.get_txid())     


    # require 3: revert if txn 1 is not a payment tx    
    with pytest.raises(AlgodHTTPError):
        payTxn = transaction.ApplicationNoOpTxn(
                sender=accounts.bad_actor.getAddress(), receiver=scripts.add_address, app_args=[b"report"], sp=suggestedParams
            )

        no_op_txn = transaction.ApplicationNoOpTxn(
            sender=scripts.tipper.getAddress(), index=scripts.feed_app_id, app_args=[b"tip"], sp=suggestedParams
        )

        signed_pay_txn = payTxn.sign(scripts.tipper.getPrivateKey())
        signed_no_op_txn = no_op_txn.sign(scripts.tipper.getPrivateKey())

        client.send_transactions([signed_pay_txn, signed_no_op_txn])

        waitForTransaction(client, no_op_txn.get_txid())  

    #assert that tx will revert if not grouped

    with pytest.raises(AlgodHTTPError):

        no_op_txn = transaction.ApplicationNoOpTxn(
            sender=scripts.tipper.getAddress(), index=scripts.feed_app_id, app_args=[b"tip"], sp=suggestedParams
        )

        signed_no_op_txn = no_op_txn.sign(scripts.tipper.getPrivateKey())

        client.send_transactions([signed_no_op_txn])

        waitForTransaction(client, no_op_txn.get_txid())  


    
    # assert that the tip_amount state variable is equal to
    # the algo transferred in txn 1 

    state = getAppGlobalState(client, deployed_contract.id)
    prev_tip_amount = state[b"tip_amount"]

    scripts.tip()

    state = getAppGlobalState(client, deployed_contract.id)
    curr_tip_amount = state[b"tip_amount"]

    assert curr_tip_amount == prev_tip_amount + tip_amount


def test_vote(client, scripts, accounts, deployed_contract):
    """Test vote() method on contract"""
    scripts.stake()
    state = getAppGlobalState(client, deployed_contract.id)
    num_reports = state[b"num_reports"]
    scripts.vote(1)

    state = getAppGlobalState(client, deployed_contract.id)
    num_reports += 1  # number of reports increases by 1
    assert state[b"num_reports"] == num_reports
    assert state[b"staking_status"] == 1

    scripts.vote(0)
    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"num_reports"] == num_reports  # number of reports doesn't increase nor decrease after slashing
    assert state[b"staking_status"] == 0

def test_withdraw_request(client, scripts, accounts, deployed_contract):
    """Test withdraw_request() method on feed contract"""

    #require 2: assert unstaked account can't request withdrawal
    with pytest.raises(AlgodHTTPError):
        scripts.withdraw_request()

    #stake reporter
    scripts.stake()

    #require 1: assert bad actor cant begin
    #withdrawal when reporter is staked
    scripts.reporter = accounts.bad_actor
    with pytest.raises(AlgodHTTPError):
        scripts.withdraw_request()

    state = getAppGlobalState(client, deployed_contract.id)

    #assert staking status before fn call is 1
    assert state[b"staking_status"] == 1

    #assert stake_timestamp is 0
    assert state[b"stake_timestamp"] == 0

    #call withdraw_request
    scripts.withdraw_request()

    #get state again
    state = getAppGlobalState(client, deployed_contract.id)

    #assert stake timestamp is now approx. time.time()
    assert state[b"stake_timestamp"] == pytest.approx(time.time(), 500)

    #assert staking status is now 2
    assert state[b"staking_status"] == 2

    #require 3: assert reporter cant request withdrawal while in state 2
    with pytest.raises(AlgodHTTPError):
        scripts.withdraw_request()


def test_withdraw(client, scripts, accounts, deployed_contract):
    """test withdraw() method on contract"""

    reporter_algo_balance_before = client.account_info(accounts.reporter.getAddress()).get("amount")
    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b"staking_status"] == 0

    scripts.stake()
    state = getAppGlobalState(client, deployed_contract.id)

    assert state[b"staking_status"] == 1

    scripts.withdraw_request()

    state = getAppGlobalState(client, deployed_contract.id)
    assert state[b"staking_status"] == 2

    tx_fee = 2000

    state = getAppGlobalState(client, deployed_contract.id)

    reporter_algo_balance_after = client.account_info(accounts.reporter.getAddress()).get("amount")

    assert state[b"staking_status"] == 0
    assert reporter_algo_balance_after == reporter_algo_balance_before - tx_fee * 2
