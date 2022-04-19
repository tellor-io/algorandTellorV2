import time
from typing import Any
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from algosdk.atomic_transaction_composer import AtomicTransactionComposer
from algosdk.atomic_transaction_composer import MultisigTransactionSigner
from algosdk.atomic_transaction_composer import TransactionWithSigner
from algosdk.future import transaction
from algosdk.future.transaction import create_dryrun
from algosdk.future.transaction import Multisig
from algosdk.logic import get_application_address
from algosdk.v2client.algod import AlgodClient

from src.contracts.contracts import approval_program
from src.contracts.contracts import clear_state_program
from src.contracts.medianizer_contract import approval_program as approval_medianizer
from src.contracts.medianizer_contract import clear_state_program as clear_medianizer
from src.utils.account import Account
from src.utils.util import fullyCompileContract
from src.utils.util import getAppGlobalState
from src.utils.util import waitForTransaction


APPROVAL_PROGRAM = b""
CLEAR_STATE_PROGRAM = b""

MEDIANIZER_APPROVAL_PROGRAM = b""
MEDIANIZER_CLEAR_STATE_PROGRAM = b""


class Scripts:
    """
    A collection of helper scripts for quickly calling contract methods
    used only for testing and deploying

    note:
    these scripts are only examples.
    they haven't been audited.
    other scripts will do just fine to call the contract methods.

    """

    def __init__(
        self,
        client: AlgodClient,
        tipper: Account,
        reporter: Account,
        governance_address: Union[Account, Multisig],
        feed_app_id: Optional[int] = None,
        medianizer_app_id: Optional[int] = None,
        contract_count: Optional[int] = 1,
    ) -> None:
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
        self.feed_app_id = feed_app_id
        self.medianizer_app_id = medianizer_app_id
        self.contract_count = contract_count

        self.feeds = []

        if self.feed_app_id is not None:
            self.feed_app_address = get_application_address(self.feed_app_id)
        if self.medianizer_app_id is not None:
            self.medianizer_app_address = get_application_address(self.medianizer_app_id)

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

    def get_contracts_medianizer(self, client: AlgodClient) -> Tuple[bytes, bytes]:
        """
        Get the compiled TEAL contracts for the tellor contract.

        Args:
            client: An algod client that has the ability to compile TEAL programs.
        Returns:
            A tuple of 2 byte strings. The first is the approval program, and the
            second is the clear state program.
        """
        global MEDIANIZER_APPROVAL_PROGRAM
        global MEDIANIZER_CLEAR_STATE_PROGRAM

        if len(MEDIANIZER_APPROVAL_PROGRAM) == 0:
            MEDIANIZER_APPROVAL_PROGRAM = fullyCompileContract(client, approval_medianizer())
            MEDIANIZER_CLEAR_STATE_PROGRAM = fullyCompileContract(client, clear_medianizer())

        return MEDIANIZER_APPROVAL_PROGRAM, MEDIANIZER_CLEAR_STATE_PROGRAM

    def get_medianized_value(self):

        state = getAppGlobalState(self.client, self.medianizer_app_id)

        return state["median"]

    def get_current_feeds(self):

        state = getAppGlobalState(self.client, self.medianizer_app_id)

        current_data = {}

        for i in range(5):
            feed_app_id = state["app_" + i]
            feed_state = getAppGlobalState(self.client, feed_app_id)
            current_data[feed_app_id]["values"] = feed_state["values"]
            current_data[feed_app_id]["timestamps"] = feed_state["timestamps"]

    def deploy_tellor_flex(
        self, query_id: str, query_data: str, timestamp_freshness: int, multisigaccounts_sk: List[str]
    ) -> int:
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

        globalSchema = transaction.StateSchema(num_uints=10, num_byte_slices=9)
        localSchema = transaction.StateSchema(num_uints=0, num_byte_slices=0)
        medianizer_id = 0
        app_args = [query_id.encode("utf-8"), query_data.encode("utf-8"), medianizer_id, timestamp_freshness]

        print(f"Forming {self.contract_count} {query_id} contracts")
        for i in range(self.contract_count):
            comp = AtomicTransactionComposer()
            comp.add_transaction(
                TransactionWithSigner(
                    transaction.ApplicationCreateTxn(
                        sender=self.governance_address.address(),
                        on_complete=transaction.OnComplete.NoOpOC,
                        approval_program=approval,
                        clear_program=clear,
                        global_schema=globalSchema,
                        local_schema=localSchema,
                        app_args=app_args,
                        sp=self.client.suggested_params(),
                        note=f"{query_id} Feed {i}".encode(),
                    ),
                    MultisigTransactionSigner(self.governance_address, multisigaccounts_sk),
                )
            )
            txid = comp.execute(self.client, 4).tx_ids
            for i in txid:
                res = self.client.pending_transaction_info(i)
                app_id = res["application-index"]
                self.feeds.append(app_id)

        print("Created new apps:", self.feeds)
        return self.feeds

    def deploy_medianizer(self, timestamp_freshness: int, query_id: bytes, multisigaccounts_sk: List[int]) -> int:
        approval, clear = self.get_contracts_medianizer(self.client)

        global_schema = transaction.StateSchema(num_uints=7, num_byte_slices=7)
        local_schema = transaction.StateSchema(num_uints=0, num_byte_slices=0)

        app_args = [timestamp_freshness, query_id]
        comp = AtomicTransactionComposer()
        comp.add_transaction(
            TransactionWithSigner(
                transaction.ApplicationCreateTxn(
                    sender=self.governance_address.address(),
                    sp=self.client.suggested_params(),
                    on_complete=transaction.OnComplete.NoOpOC,
                    approval_program=approval,
                    clear_program=clear,
                    global_schema=global_schema,
                    local_schema=local_schema,
                    app_args=app_args,
                ),
                MultisigTransactionSigner(self.governance_address, multisigaccounts_sk),
            )
        )
        tx_id = comp.execute(self.client, 4).tx_ids
        res = self.client.pending_transaction_info(tx_id[0])
        self.medianizer_app_id = res["application-index"]
        print(f"Created medianizer app: {self.medianizer_app_id}")
        return self.medianizer_app_id

    def activate_contract(self, multisigaccounts_sk: List[Any]) -> List[int]:
        comp = AtomicTransactionComposer()
        comp.add_transaction(
            TransactionWithSigner(
                transaction.ApplicationNoOpTxn(
                    sender=self.governance_address.address(),
                    sp=self.client.suggested_params(),
                    index=self.medianizer_app_id,
                    app_args=["activate_contract"],
                    foreign_apps=self.feeds,
                ),
                MultisigTransactionSigner(self.governance_address, multisigaccounts_sk),
            )
        )
        tx_id = comp.execute(self.client, 4).tx_ids
        print(f"Medianizer active, tx hash: {tx_id}")
        return tx_id

    def set_medianizer(self, multisigaccounts_sk: List[Any]) -> List[int]:
        txn_ids = []
        for i in self.feeds:
            comp = AtomicTransactionComposer()
            comp.add_transaction(
                TransactionWithSigner(
                    transaction.ApplicationNoOpTxn(
                        sender=self.governance_address.address(),
                        sp=self.client.suggested_params(),
                        index=i,
                        app_args=["change_medianizer", self.medianizer_app_id],
                    ),
                    MultisigTransactionSigner(self.governance_address, multisigaccounts_sk),
                )
            )
            tx_id = comp.execute(self.client, 3).tx_ids
            txn_ids.append(tx_id[0])
        return txn_ids

    def stake(self, stake_amount=None) -> None:
        """
        Send 2-txn group transaction to...
        - send the stake amount from the reporter to the contract
        - call stake() on the contract

        Args:
            stake_amount (int): override stake_amount for testing purposes
        """
        appGlobalState = getAppGlobalState(self.client, self.feed_app_id)

        if stake_amount is None:
            stake_amount = appGlobalState[b"stake_amount"]

        suggestedParams = self.client.suggested_params()

        payTxn = transaction.PaymentTxn(
            sender=self.reporter.getAddress(),
            receiver=self.feed_app_address,
            amt=stake_amount,
            sp=suggestedParams,
        )

        stakeInTx = transaction.ApplicationNoOpTxn(
            sender=self.reporter.getAddress(),
            index=self.feed_app_id,
            app_args=[b"stake"],
            sp=self.client.suggested_params(),
        )

        transaction.assign_group_id([payTxn, stakeInTx])

        signedPayTxn = payTxn.sign(self.reporter.getPrivateKey())
        signedAppCallTxn = stakeInTx.sign(self.reporter.getPrivateKey())

        self.client.send_transactions([signedPayTxn, signedAppCallTxn])

        waitForTransaction(self.client, stakeInTx.get_txid())

    def tip(self, tip_amount: int) -> None:

        suggestedParams = self.client.suggested_params()

        payTxn = transaction.PaymentTxn(
            sender=self.tipper.getAddress(), receiver=self.feed_app_address, amt=tip_amount, sp=suggestedParams
        )

        no_op_txn = transaction.ApplicationNoOpTxn(
            sender=self.tipper.getAddress(), index=self.feed_app_id, app_args=[b"tip"], sp=suggestedParams
        )

        transaction.assign_group_id([payTxn, no_op_txn])

        signed_pay_txn = payTxn.sign(self.tipper.getPrivateKey())
        signed_no_op_txn = no_op_txn.sign(self.tipper.getPrivateKey())

        self.client.send_transactions([signed_pay_txn, signed_no_op_txn])

        waitForTransaction(self.client, no_op_txn.get_txid())

    def report(self, query_id: bytes, value: bytes, timestamp: int):
        """
        Call report() on the contract to set the current value on the contract

        Args:
            - query_id (bytes): the unique identifier representing the type of data requested
            - value (bytes): the data the reporter submits on chain
        """

        submitValueTxn = transaction.ApplicationNoOpTxn(
            sender=self.reporter.getAddress(),
            accounts=[self.governance_address.address()],
            index=self.feed_app_id,
            app_args=[b"report", query_id, value, timestamp],
            foreign_apps=self.feeds + [self.medianizer_app_id],
            sp=self.client.suggested_params(),
        )

        signedSubmitValueTxn = submitValueTxn.sign(self.reporter.getPrivateKey())
        self.client.send_transaction(signedSubmitValueTxn)
        waitForTransaction(self.client, signedSubmitValueTxn.get_txid(), timeout=30)

    def withdraw(self, ff_time: int = 0):
        """
        Sends the reporter their stake back and removes their permission to report
        calls withdraw() on the contract
        """

        if ff_time == 0:
            txn = transaction.ApplicationNoOpTxn(
                sender=self.reporter.getAddress(),
                index=self.feed_app_id,
                app_args=[b"withdraw"],
                sp=self.client.suggested_params(),
            )
            signedTxn = txn.sign(self.reporter.getPrivateKey())
            self.client.send_transaction(signedTxn)
            waitForTransaction(self.client, signedTxn.get_txid())
        else:
            txn = transaction.ApplicationNoOpTxn(
                sender=self.reporter.getAddress(),
                index=self.feed_app_id,
                app_args=[b"withdraw"],
                sp=self.client.suggested_params(),
            )
            signedTxn = txn.sign(self.reporter.getPrivateKey())
            dr_request = create_dryrun(self.client, [txn], latest_timestamp=time.time() + ff_time)
            dr_response = self.client.dryrun(dr_request)
            dr_result = dr_request.DryrunResponse(dr_response)
            for txn in dr_result.txns:
                if txn.app_call_rejected():
                    print(txn.app_trace(dryrun_results.StackPrinterConfig(max_value_width=0)))

    def request_withdraw(self):
        """
        locks reporter for 7 days before being allowed to withdraw stake
        """
        txn = transaction.ApplicationNoOpTxn(
            sender=self.reporter.getAddress(),
            index=self.feed_app_id,
            app_args=[b"request_withdraw"],
            sp=self.client.suggested_params(),
        )
        signedTxn = txn.sign(self.reporter.getPrivateKey())
        self.client.send_transaction(signedTxn)
        waitForTransaction(self.client, signedTxn.get_txid())

    def withdraw_dry(self, txns: List = [], timestamp: int = 0):
        """
        locks reporter for 7 days before being allowed to withdraw stake
        """
        txn = transaction.ApplicationNoOpTxn(
            sender=self.reporter.getAddress(),
            index=self.feed_app_id,
            app_args=[b"withdraw"],
            sp=self.client.suggested_params(),
        )
        signedTxn = txn.sign(self.reporter.getPrivateKey())
        dryrun = transaction.create_dryrun(client=self.client, txns=[signedTxn] + txns, latest_timestamp=timestamp)
        dryrun_response = self.client.dryrun(dryrun)

        return dryrun_response

    def slash_reporter(self, multisigaccounts_sk: List[Any]) -> int:
        """
        governance slashes reporter for bad report
        """
        comp = AtomicTransactionComposer()
        comp.add_transaction(
            TransactionWithSigner(
                transaction.ApplicationNoOpTxn(
                    sender=self.governance_address.address(),
                    sp=self.client.suggested_params(),
                    index=self.feed_app_id,
                    app_args=["slash_reporter"],
                ),
                MultisigTransactionSigner(self.governance_address, multisigaccounts_sk),
            )
        )
        txn_id = comp.execute(self.client, 3).tx_ids
        return txn_id
