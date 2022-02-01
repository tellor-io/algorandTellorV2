from typing import Tuple, List

from algosdk.v2client.algod import AlgodClient
from algosdk.future import transaction
from algosdk.logic import get_application_address
from algosdk import account, encoding

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

        globalSchema = transaction.StateSchema(num_uints=7, num_byte_slices=5)
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
        # appGlobalState = getAppGlobalState(client, appID)

        # if any(appGlobalState[b"bid_account"]):
        #     # if "bid_account" is not the zero address
        #     prevBidLeader = encoding.encode_address(appGlobalState[b"bid_account"])
        # else:
        #     prevBidLeader = None

        stake_amount = 100000 #200 dollars of ALGO

        suggestedParams = self.client.suggested_params()

        payTxn = transaction.PaymentTxn(
            sender=self.reporter.getAddress(),
            receiver=self.app_address,
            amt=stake_amount,
            sp=suggestedParams,
        )

        optInTx = transaction.ApplicationOptInTxn(
            sender=self.reporter.getAddress(),
            index=self.app_id,
            sp=suggestedParams,
        )

        transaction.assign_group_id([payTxn, optInTx])

        signedPayTxn = payTxn.sign(self.reporter.getPrivateKey())
        signedAppCallTxn = optInTx.sign(self.reporter.getPrivateKey())

        self.client.send_transactions([signedPayTxn, signedAppCallTxn])

        waitForTransaction(self.client, optInTx.get_txid())

    def report():
        pass
    
    def vote():
        pass

    def withdraw():
        pass

    def close():
        pass

    def closeAuction(self, client: AlgodClient, appID: int, closer: Account):
        """Close an auction.
        This action can only happen before an auction has begun, in which case it is
        cancelled, or after an auction has ended.
        If called after the auction has ended and the auction was successful, the
        NFT is transferred to the winning bidder and the auction proceeds are
        transferred to the seller. If the auction was not successful, the NFT and
        all funds are transferred to the seller.
        Args:
            client: An Algod client.
            appID: The app ID of the auction.
            closer: The account initiating the close transaction. This must be
                either the seller or auction creator if you wish to close the
                auction before it starts. Otherwise, this can be any account.
        """
        appGlobalState = getAppGlobalState(client, appID)

        nftID = appGlobalState[b"nft_id"]

        accounts: List[str] = [encoding.encode_address(appGlobalState[b"seller"])]

        if any(appGlobalState[b"bid_account"]):
            # if "bid_account" is not the zero address
            accounts.append(encoding.encode_address(appGlobalState[b"bid_account"]))

        deleteTxn = transaction.ApplicationDeleteTxn(
            sender=closer.getAddress(),
            index=appID,
            accounts=accounts,
            foreign_assets=[nftID],
            sp=client.suggested_params(),
        )
        signedDeleteTxn = deleteTxn.sign(closer.getPrivateKey())

        client.send_transaction(signedDeleteTxn)

        waitForTransaction(client, signedDeleteTxn.get_txid())

if __name__ == "__main__":

    def setup():
        algo_address = "http://localhost:4001"
        algo_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

        client = AlgodClient(algod_address=algo_address, algod_token=algo_token)

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

    s = setup()
    app_id = s.deploy_tellor_flex(
        query_id="hi",
        query_data="hi",
    )

    s.stake()