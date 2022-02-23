import os
from typing import Tuple

from algosdk import encoding
from algosdk.future import transaction
from algosdk.logic import get_application_address
from algosdk.v2client.algod import AlgodClient
from dotenv import load_dotenv

from src.contracts.contracts import approval_program
from src.contracts.contracts import clear_state_program
from src.utils.account import Account
from src.utils.helpers import add_standalone_account
from src.utils.helpers import fund_account
from src.utils.util import fullyCompileContract
from src.utils.util import getAppGlobalState
from src.utils.util import waitForTransaction

APPROVAL_PROGRAM = b""
CLEAR_STATE_PROGRAM = b""


class Scripts:
    """
    A collection of helper scripts for quickly calling contract methods
    used only for testing and deploying

    note:
    these scripts are only examples.
    they haven't been audited.
    other scripts will do just fine to call the contract methods.

    """

    def __init__(self, client: AlgodClient, tipper: Account, reporter: Account, governance_address: Account) -> None:
        """
        - connects to algorand node
        - initializes some dummy accounts used for contract testing

        Args:
            client (AlgodClient): the algorand node we connect to read state and send transactions
            tipper (src.utils.account.Account): an account that deploys the contract and requests data
            reporter (src.utils.account.Account): an account that stakes ALGO tokens and submits data
            governance_address (src.utils.account.Account): an account that decides the quality of the reporter's data

        """

        self.client = client
        self.tipper = tipper
        self.reporter = reporter
        self.governance_address = governance_address

    def get_contracts(self, client: AlgodClient) -> Tuple[bytes, bytes]:
        """
        Get the compiled TEAL contracts for the tellor contract.

        Args:
            client: An algod client that has the ability to compile TEAL programs.
        Returns:
            A tuple of 2 byte strings. The first is the approval program, and the
            second is the clear state program.
        """
        global APPROVAL_PROGRAM
        global CLEAR_STATE_PROGRAM

        if len(APPROVAL_PROGRAM) == 0:
            APPROVAL_PROGRAM = fullyCompileContract(client, approval_program())
            CLEAR_STATE_PROGRAM = fullyCompileContract(client, clear_state_program())

        return APPROVAL_PROGRAM, CLEAR_STATE_PROGRAM

    def deploy_tellor_flex(self, query_id: str, query_data: str) -> int:
        """
        Deploy a new tellor reporting contract.
        calls create() method on contract

        Args:
            client: An algod client.
            sender: The account that will request data through the contract
            governance_address: the account that can vote to dispute reports
            query_id: the ID of the data requested to be put on chain
            query_data: the in-depth specifications of the data requested
        Returns:
            int: The ID of the newly created auction app.
        """
        approval, clear = self.get_contracts(self.client)

        globalSchema = transaction.StateSchema(num_uints=7, num_byte_slices=6)
        localSchema = transaction.StateSchema(num_uints=0, num_byte_slices=0)

        app_args = [
            encoding.decode_address(self.governance_address.getAddress()),
            query_id.encode("utf-8"),
            query_data.encode("utf-8"),
        ]

        txn = transaction.ApplicationCreateTxn(
            sender=self.tipper.getAddress(),
            on_complete=transaction.OnComplete.NoOpOC,
            approval_program=approval,
            clear_program=clear,
            global_schema=globalSchema,
            local_schema=localSchema,
            app_args=app_args,
            sp=self.client.suggested_params(),
        )

        signedTxn = txn.sign(self.tipper.getPrivateKey())

        self.client.send_transaction(signedTxn)

        response = waitForTransaction(self.client, signedTxn.get_txid())
        assert response.applicationIndex is not None and response.applicationIndex > 0
        self.app_id = response.applicationIndex
        self.app_address = get_application_address(self.app_id)
        return self.app_id

    def stake(self, stake_amount=None) -> None:
        """
        Send 2-txn group transaction to...
        - send the stake amount from the reporter to the contract
        - call stake() on the contract

        Args:
            stake_amount (int): override stake_amount for testing purposes
        """
        appGlobalState = getAppGlobalState(self.client, self.app_id)

        if stake_amount is None:
            stake_amount = appGlobalState[b"stake_amount"]

        suggestedParams = self.client.suggested_params()

        payTxn = transaction.PaymentTxn(
            sender=self.reporter.getAddress(),
            receiver=self.app_address,
            amt=stake_amount,
            sp=suggestedParams,
        )

        stakeInTx = transaction.ApplicationNoOpTxn(
            sender=self.reporter.getAddress(), index=self.app_id, app_args=[b"stake"], sp=self.client.suggested_params()
        )

        transaction.assign_group_id([payTxn, stakeInTx])

        signedPayTxn = payTxn.sign(self.reporter.getPrivateKey())
        signedAppCallTxn = stakeInTx.sign(self.reporter.getPrivateKey())

        self.client.send_transactions([signedPayTxn, signedAppCallTxn])

        waitForTransaction(self.client, stakeInTx.get_txid())

    def report(self, query_id: bytes, value: bytes):
        """
        Call report() on the contract to set the current value on the contract

        Args:
            - query_id (bytes): the unique identifier representing the type of data requested
            - value (bytes): the data the reporter submits on chain
        """

        submitValueTxn = transaction.ApplicationNoOpTxn(
            sender=self.reporter.getAddress(),
            index=self.app_id,
            app_args=[b"report", query_id, value],
            sp=self.client.suggested_params(),
        )

        signedSubmitValueTxn = submitValueTxn.sign(self.reporter.getPrivateKey())
        self.client.send_transaction(signedSubmitValueTxn)
        waitForTransaction(self.client, signedSubmitValueTxn.get_txid())

    def vote(self, gov_vote: int):
        """
        Use the governance contract to approve or deny a value
        calls vote() on the contract, only callable by governance address

        0 means rejected
        1 means approved

        Args:
            gov_vote (int, 0 or 1): binary decision to approve or reject a value
        """

        txn = transaction.ApplicationNoOpTxn(
            sender=self.governance_address.getAddress(),
            index=self.app_id,
            app_args=[b"vote", gov_vote],
            sp=self.client.suggested_params(),
        )
        signedTxn = txn.sign(self.governance_address.getPrivateKey())
        self.client.send_transaction(signedTxn)
        waitForTransaction(self.client, signedTxn.get_txid())

    def withdraw(self):
        """
        Sends the reporter their stake back and removes their permission to report
        calls withdraw() on the contract
        """
        txn = transaction.ApplicationNoOpTxn(
            sender=self.reporter.getAddress(),
            index=self.app_id,
            app_args=[b"withdraw"],
            sp=self.client.suggested_params(),
        )
        signedTxn = txn.sign(self.reporter.getPrivateKey())
        self.client.send_transaction(signedTxn)
        waitForTransaction(self.client, signedTxn.get_txid())


if __name__ == "__main__":
    """
    quick deployment scheme, works on:
     - local private network
     - algorand public testnet
    """

    def setup(testnet=False):
        """helper function to setup deployment"""

        load_dotenv()

        algo_address = "http://localhost:4001"
        algo_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

        client = AlgodClient(algod_address=algo_address, algod_token=algo_token)

        tipper = Account.FromMnemonic(os.getenv("MNEMONIC"))
        gov_address = add_standalone_account()
        reporter = add_standalone_account()

        if testnet is False:
            tipper = add_standalone_account()

            fund_account(gov_address)
            fund_account(tipper)
            fund_account(reporter)

        print("gov", gov_address.getAddress())
        print("tipper", tipper.getAddress())
        print("reporter", reporter.getAddress())

        s = Scripts(client=client, tipper=tipper, reporter=reporter, governance_address=gov_address)

        return s

    s = setup(testnet=True)
    app_id = s.deploy_tellor_flex(
        query_id="hi",
        query_data="hi",
    )

    print("App deployed. App id: ", app_id)

    # s.stake()
