import base64
import time

import pytest
from algosdk import encoding
from algosdk.error import AlgodHTTPError
from algosdk.future import transaction
from algosdk.logic import get_application_address
from src.scripts.scripts import Scripts

from src.utils.util import getAppGlobalState, waitForTransaction
from src.utils.senders import send_no_op_tx
from src.utils.testing.resources import getTemporaryAccount
from conftest import App

def test_change_governance(client, scripts:Scripts, accounts, deployed_contract:App):

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    old_gov_address = state[b"governance_address"]
    new_gov_address = getTemporaryAccount(client).addr
    
    #require 1: should revert if not called by current governance address
    with pytest.raises(AlgodHTTPError):
        send_no_op_tx(accounts.bad_actor, deployed_contract.feed_ids[0], fn_name="change_governance", app_args=[new_gov_address], foreign_apps=None)

    #require 2: should revert if no new governance address is submitted
    with pytest.raises(AlgodHTTPError):
        send_no_op_tx(accounts.governance, deployed_contract.feed_ids[0], fn_name="change_governance")

    send_no_op_tx(accounts.governance, deployed_contract.feed_ids[0], fn_name="change_governance", app_args=[new_gov_address])

    #assert governance should be a different address

    state = getAppGlobalState(client, deployed_contract)
    assert state[b"governance_address"] == new_gov_address


def test_change_medianizer(client, scripts, accounts, deployed_contract):

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    old_medianizer_id = state[b"medianizer"]
    new_medianizer_id = 1234
    
    #require 1: should revert if not called by current governance address
    with pytest.raises(AlgodHTTPError):
        send_no_op_tx(accounts.bad_actor, deployed_contract.feed_ids[0], fn_name="change_medianizer", foreign_apps=[new_medianizer_id], app_args=None)

    #require 2: should revert if no new governance address is submitted
    with pytest.raises(AlgodHTTPError):
        send_no_op_tx(accounts.governance, deployed_contract.feed_ids[0], fn_name="change_medianizer")

    send_no_op_tx(accounts.governance, deployed_contract.feed_ids[0], fn_name="change_medianizer", foreign_apps=[new_medianizer_id], app_args=None)

    #assert governance should be a different address

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    assert state[b"medianizer"] == new_medianizer_id
    
def test_activate_contract(client, scripts, accounts, deployed_contract):
    """Test activate_contract method on medianizer_contract"""

    medianzier_state = getAppGlobalState(client, deployed_contract.medianizer_id)
    n = 1
    for i in deployed_contract.feed_ids:
        feed_state = getAppGlobalState(client, i)
        app = "app_" + f"{n}"
        encoded = app.encode('utf-8')
        addr = get_application_address(i)
        n+=1
        assert medianzier_state[encoded] == encoding.decode_address(addr)
        assert feed_state[b"medianizer"] == deployed_contract.medianizer_id

    assert medianzier_state[b"governance"] == encoding.decode_address(accounts.governance.address())


def test_get_values(client, scripts, accounts, deployed_contract):
    """Test get_values() method on medianizer_contract"""
    medianzier_state = getAppGlobalState(client, deployed_contract.medianizer_id)

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    scripts.feed_app_address = get_application_address(scripts.feed_app_id)

    scripts.stake()

    for i in deployed_contract.feed_ids:
        feed_state = getAppGlobalState(client, i)
        assert feed_state[b"num_reports"] == 0

    query_id = b"1"
    value = 1234
    timestamp = 5678
    scripts.report(query_id, value, timestamp)
    assert feed_state[b"query_id"] == query_id
    assert feed_state[b"value"] == value
    assert feed_state[b"timestamp"] == timestamp

    scripts.get_values()
    assert medianzier_state["median_price"] == value
    assert medianzier_state["median_timestamp"] == timestamp


def test_report(client, scripts, accounts, deployed_contract:App):
    """Test report() method on contract"""

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    scripts.feed_app_address = get_application_address(scripts.feed_app_id)

    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    assert state[b"num_reports"] == 0

    query_id = b"BTCUSD"
    value = base64.encode(39000)
    scripts.report(query_id, value)

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    assert state[b"value"] == value

    on_chain_timestamp = int(encoding.base64.b64decode(state[b"timestamp"][:6]))
    assert pytest.approx(on_chain_timestamp, 100) == int(time.time())

    new_value = b"a new data value 4567"
    scripts.report(query_id, new_value)

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    assert state[b"value"] == new_value
    on_chain_timestamp = int(encoding.base64.b64decode(state[b"timestamp"][:6]))
    assert pytest.approx(state[b"timestamp"][:6], 100) == int(time.time())


def test_stake(client, scripts:Scripts, accounts, deployed_contract:App):
    """Test stake() method on contract"""

    stake_amount = 200000

    reporter_algo_balance_before = client.account_info(accounts.reporter.getAddress()).get("amount")
    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 0
    assert state[b"reporter_address"] == b""

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    scripts.feed_app_address = get_application_address(scripts.feed_app_id)
    
    scripts.stake()

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 1
    assert state[b"reporter_address"] == encoding.decode_address(accounts.reporter.getAddress())

    reporter_algo_balance_after = client.account_info(accounts.reporter.getAddress()).get("amount")
    assert reporter_algo_balance_after == reporter_algo_balance_before - stake_amount - client.fee * 2


def test_tip(client, scripts:Scripts, accounts, deployed_contract:App):
    """Test tip() method on feed contract"""

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    scripts.feed_app_address = get_application_address(scripts.feed_app_id)

    tip_amount = 4
    suggestedParams = scripts.client.suggested_params()

    # require 1: revert if group tx senders are not the same account

    with pytest.raises(AlgodHTTPError):
        payTxn = transaction.PaymentTxn(
                sender=accounts.bad_actor.getAddress(), receiver=scripts.feed_app_address, amt=tip_amount, sp=suggestedParams
            )

        no_op_txn = transaction.ApplicationNoOpTxn(
            sender=scripts.tipper.getAddress(), index=deployed_contract.feed_ids[0], app_args=[b"tip"], sp=suggestedParams
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
            sender=scripts.tipper.getAddress(), index=deployed_contract.feed_ids[0], app_args=[b"tip"], sp=suggestedParams
        )

        signed_pay_txn = payTxn.sign(scripts.tipper.getPrivateKey())
        signed_no_op_txn = no_op_txn.sign(scripts.tipper.getPrivateKey())

        client.send_transactions([signed_pay_txn, signed_no_op_txn])

        waitForTransaction(client, no_op_txn.get_txid())     


    # require 3: revert if txn 1 is not a payment tx    
    with pytest.raises(AlgodHTTPError):
        payTxn = transaction.ApplicationNoOpTxn(
                sender=accounts.bad_actor.getAddress(), receiver=scripts.feed_app_address, app_args=[b"report"], sp=suggestedParams
            )

        no_op_txn = transaction.ApplicationNoOpTxn(
            sender=scripts.tipper.getAddress(), index=deployed_contract.feed_ids[0], app_args=[b"tip"], sp=suggestedParams
        )

        signed_pay_txn = payTxn.sign(scripts.tipper.getPrivateKey())
        signed_no_op_txn = no_op_txn.sign(scripts.tipper.getPrivateKey())

        client.send_transactions([signed_pay_txn, signed_no_op_txn])

        waitForTransaction(client, no_op_txn.get_txid())  

    #assert that tx will revert if not grouped

    with pytest.raises(AlgodHTTPError):

        no_op_txn = transaction.ApplicationNoOpTxn(
            sender=scripts.tipper.getAddress(), index=deployed_contract.feed_ids[0], app_args=[b"tip"], sp=suggestedParams
        )

        signed_no_op_txn = no_op_txn.sign(scripts.tipper.getPrivateKey())

        client.send_transactions([signed_no_op_txn])

        waitForTransaction(client, no_op_txn.get_txid())  


    
    # assert that the tip_amount state variable is equal to
    # the algo transferred in txn 1 

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    prev_tip_amount = state[b"tip_amount"]

    scripts.tip()

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    curr_tip_amount = state[b"tip_amount"]

    assert curr_tip_amount == prev_tip_amount + tip_amount


def test_slash_reporter(client, scripts:Scripts, accounts, deployed_contract:App):
    """Test vote() method on contract"""

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    scripts.feed_app_address = get_application_address(scripts.feed_app_id)
    scripts.stake()
    
    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    num_reports = state[b"num_reports"]
    scripts.vote(1)

    #require1: can only be called by the governance
    scripts.governance = accounts.bad_actor

    with pytest.raises(AlgodHTTPError):
        scripts.slash_reporter()

    #expected behavior: 
    # - gov address claims stake
    # - stake status set to 0

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    num_reports += 1  # number of reports increases by 1
    assert state[b"staking_status"] == 1
    gov_algo_balance_before = client.account_info(accounts.governance.getAddress()).get("amount")


    scripts.governance = accounts.governance

    scripts.slash_reporter()

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    assert state[b"staking_status"] == 0

    gov_algo_balance_after = client.account_info(accounts.governance.getAddress()).get("amount")

    assert gov_algo_balance_after == gov_algo_balance_before + state[b"stake_amount"]


    


def test_request_withdraw(client, scripts:Scripts, accounts, deployed_contract):
    """Test request_withdraw() method on feed contract"""

    #require 2: assert unstaked account can't request withdrawal
    with pytest.raises(AlgodHTTPError):
        scripts.request_withdraw()

    #stake reporter
    scripts.feed_app_id = deployed_contract.feed_ids[0]
    scripts.feed_app_address = get_application_address(scripts.feed_app_id)
    scripts.stake()

    #require 1: assert bad actor cant begin
    #withdrawal when reporter is staked
    scripts.reporter = accounts.bad_actor
    with pytest.raises(AlgodHTTPError):
        scripts.withdraw_request()

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    # assert staking status before fn call is 1
    assert state[b"staking_status"] == 1

    # assert stake_timestamp is 0
    assert state[b"stake_timestamp"] == 0

    # call request_withdraw
    scripts.request_withdraw()

    # get state again
    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    # assert stake timestamp is now approx. time.time()
    assert state[b"stake_timestamp"] == pytest.approx(time.time(), 500)

    # assert staking status is now 2
    assert state[b"staking_status"] == 2

    #require 3: assert reporter cant request withdrawal while in state 2
    with pytest.raises(AlgodHTTPError):
        scripts.withdraw_request()


def test_withdraw(client, scripts:Scripts, accounts, deployed_contract:App):
    """test withdraw() method on contract"""

    reporter_algo_balance_before = client.account_info(accounts.reporter.getAddress()).get("amount")
    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 0

    scripts.feed_app_id = deployed_contract.feed_ids[0]
    scripts.feed_app_address = get_application_address(scripts.feed_app_id)
    scripts.stake()
    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    assert state[b"staking_status"] == 1

    scripts.request_withdraw()

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])
    assert state[b"staking_status"] == 2

    tx_fee = 2000

    state = getAppGlobalState(client, deployed_contract.feed_ids[0])

    reporter_algo_balance_after = client.account_info(accounts.reporter.getAddress()).get("amount")

    assert state[b"staking_status"] == 0
    assert reporter_algo_balance_after == reporter_algo_balance_before - tx_fee * 2
