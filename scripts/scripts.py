import os
from typing import Tuple, List

from algosdk.v2client.algod import AlgodClient
from algosdk.future import transaction
from algosdk.logic import get_application_address
from algosdk import account, encoding
from dotenv import load_dotenv


from pyteal import compileTeal, Mode, Keccak256
from tellorflex.methods import report

from utils.account import Account
from tellorflex.contracts import approval_program, clear_state_program
from utils.helpers import add_standalone_account, fund_account
from utils.util import (
    waitForTransaction,
    fullyCompileContract,
    getAppGlobalState,
)

APPROVAL_PROGRAM = b""
CLEAR_STATE_PROGRAM = b""

class Scripts:

    def __init__(self, client, tipper, reporter, governance_address) -> None:
        
        self.client = client
        self.tipper = tipper
        self.reporter = reporter
        self.governance_address = governance_address.getAddress()

        self.flat_fee = 2000 #0.002 Algos

    def get_contracts(self, client: AlgodClient) -> Tuple[bytes, bytes]:
        """Get the compiled TEAL contracts for the tellor contract.
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

    def deploy_tellor_flex(
        self,
        query_id: str,
        query_data: str
    ) -> int:
        """Create a new tellor reporting contract.
        Args:
            client: An algod client.
            sender: The account that will request data through the contract
            governance_address: the account that can vote to dispute reports
            query_id: the ID of the data requested to be put on chain
            query_data: the in-depth specifications of the data requested
        Returns:
            The ID of the newly created auction app.
        """
        approval, clear = self.get_contracts(self.client)

        globalSchema = transaction.StateSchema(num_uints=7, num_byte_slices=6)
        localSchema = transaction.StateSchema(num_uints=0, num_byte_slices=0)

        app_args = [
            encoding.decode_address(self.governance_address),
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

    def stake(self) -> None:
        """Place a bid on an active auction.
        Args:
            client: An Algod client.
            appID: The app ID of the auction.
            reporter: The account staking to report.
        """
        appAddr = get_application_address(self.app_id)
        appGlobalState = getAppGlobalState(self.client, self.app_id)

        # if any(appGlobalState[b"bid_account"]):
        #     # if "bid_account" is not the zero address
        #     prevBidLeader = encoding.encode_address(appGlobalState[b"bid_account"])
        # else:
        #     prevBidLeader = None
        '''no longer an optin
        # add args [b"stake"]'''
        # stake_amount = 100000 #200 dollars of ALGO

        suggestedParams = self.client.suggested_params()

        payTxn = transaction.PaymentTxn(
            sender=self.reporter.getAddress(),
            receiver=self.app_address,
            amt=appGlobalState[b'stake_amount'],
            sp=suggestedParams,
        )

        stakeInTx = transaction.ApplicationNoOpTxn(
            sender=self.reporter.getAddress(),
            index=self.app_id,
            app_args=[b'stake'],
            sp=self.client.suggested_params()
        )

        transaction.assign_group_id([payTxn, stakeInTx])

        signedPayTxn = payTxn.sign(self.reporter.getPrivateKey())
        signedAppCallTxn = stakeInTx.sign(self.reporter.getPrivateKey())

        self.client.send_transactions([signedPayTxn, signedAppCallTxn])

        waitForTransaction(self.client, stakeInTx.get_txid())

    def report(self,query_id: bytes, value: bytes):
        # value = value.encode('utf-8')

        submitValueTxn = transaction.ApplicationNoOpTxn(
            sender=self.reporter.getAddress(),
            index=self.app_id,
            app_args=[b'report',query_id, value],
            sp=self.client.suggested_params()
        )

        signedSubmitValueTxn = submitValueTxn.sign(self.reporter.getPrivateKey())
        self.client.send_transaction(signedSubmitValueTxn)
        waitForTransaction(self.client, signedSubmitValueTxn.get_txid())

    
    def vote(self, vote: int):
        if not(vote == 0 or vote == 1):
            raise ValueError

        txn = transaction.ApplicationNoOpTxn(
            sender=self.governance_address,
            index=self.app_id,
            app_args=[b'vote',vote],
            sp=self.client.suggested_params(),
        )
        signedTxn = txn.sign(self.governance_address.getPrivateKey())
        self.client.send_transaction(signedTxn)
        response = waitForTransaction(self.client, signedTxn.get_txid())
        

    def withdraw(self):
        appGlobalState = getAppGlobalState(self.client, self.app_id)
        '''should be a noop txn'''
        txn = transaction.ApplicationNoOpTxn(
            sender=self.reporter.getAddress(),
            index=self.app_id,
            on_complete=transaction.OnComplete.NoOpOC,
            app_args=[b'withdraw'],
            sp=self.client.suggested_params(),
        )
        signedTxn = txn.sign(self.app_address.getPrivateKey())
        self.client.send_transaction(signedTxn)
        waitForTransaction(self.client, signedTxn.get_txid())
        assert appGlobalState[b'staking_status'] == 0

    def close(self):

        closeOutTxn = transaction.ApplicationCloseOutTxn(
            sender=self.governance_address(),
            index=self.app_id,
            app_args=['close'],
            sp=self.client.suggested_params(),
        )
        
        signedcloseOutTxn = closeOutTxn.sign(self.governance_address().getPrivateKey())
        self.client.send_transaction(signedcloseOutTxn)
        waitForTransaction(self.client, signedcloseOutTxn.get_txid())

if __name__ == "__main__":

    def setup(testnet=False):

        load_dotenv()

        algo_address = "http://localhost:4001"
        algo_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

        client = AlgodClient(algod_address=algo_address, algod_token=algo_token)

        tipper = Account.FromMnemonic(os.getenv("MNEMONIC"))

        if testnet == False:
            gov_address = add_standalone_account()
            reporter = add_standalone_account()
            tipper = add_standalone_account()            

            fund_account(gov_address)
            fund_account(tipper)
            fund_account(reporter)

        print("gov", gov_address.getAddress())
        print("tipper", tipper.getAddress())
        print("reporter", reporter.getAddress())

        s = Scripts(client=client, tipper=tipper, reporter=reporter, governance_address=gov_address)

        return s

    s = setup(testnet=False)
    app_id = s.deploy_tellor_flex(
        query_id="hi",
        query_data="hi",
    )

    print("App deployed. App id: ", app_id)

    s.stake()