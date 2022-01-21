from typing import Tuple, List

from algosdk.v2client.algod import AlgodClient
from algosdk.future import transaction
from algosdk.logic import get_application_address
from algosdk import account, encoding

from pyteal import compileTeal, Mode

from .account import Account
from .contracts import approval_program, clear_state_program
from .util import (
    waitForTransaction,
    fullyCompileContract,
    getAppGlobalState,
)

APPROVAL_PROGRAM = b""
CLEAR_STATE_PROGRAM = b""


def get_contracts(client: AlgodClient) -> Tuple[bytes, bytes]:
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
    client: AlgodClient,
    sender: Account,
    governance_address: Account,
    stake_amount: int,
    query_id: str,
    query_data: str
) -> int:
    """Create a new tellor reporting contract.
    Args:
        client: An algod client.
        sender: The account that will create the auction application.
        governance_address: the account that can vote to change the
                            properties of the contract
        stake_amount: the amount of tokens needed to submit a value
        query_id: the ID of the data requested to be put on chain
        query_data: the in-depth specifications of the data requested
    Returns:
        The ID of the newly created auction app.
    """
    approval, clear = get_contracts(client)

    globalSchema = transaction.StateSchema(num_uints=7, num_byte_slices=2)
    localSchema = transaction.StateSchema(num_uints=0, num_byte_slices=0)

    app_args = [
        encoding.decode_address(governance_address),
        stake_amount.to_bytes(8, "big"),
        query_id.to_bytes(32, "big"),
        query_data.to_bytes(256, "big"),
    ]

    txn = transaction.ApplicationCreateTxn(
        sender=sender.getAddress(),
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval,
        clear_program=clear,
        global_schema=globalSchema,
        local_schema=localSchema,
        app_args=app_args,
        sp=client.suggested_params(),
    )

    signedTxn = txn.sign(sender.getPrivateKey())

    client.send_transaction(signedTxn)

    response = waitForTransaction(client, signedTxn.get_txid())
    assert response.applicationIndex is not None and response.applicationIndex > 0
    return response.applicationIndex

def stake(client: AlgodClient, appID: int, reporter: Account, bidAmount: int) -> None:
    """Place a bid on an active auction.
    Args:
        client: An Algod client.
        appID: The app ID of the auction.
        reporter: The account staking to report.
        bidAmount: The amount of the bid.
    """
    appAddr = get_application_address(appID)
    appGlobalState = getAppGlobalState(client, appID)

    nftID = appGlobalState[b"nft_id"]

    if any(appGlobalState[b"bid_account"]):
        # if "bid_account" is not the zero address
        prevBidLeader = encoding.encode_address(appGlobalState[b"bid_account"])
    else:
        prevBidLeader = None

    suggestedParams = client.suggested_params()

    payTxn = transaction.PaymentTxn(
        sender=bidder.getAddress(),
        receiver=appAddr,
        amt=bidAmount,
        sp=suggestedParams,
    )

    appCallTxn = transaction.ApplicationCallTxn(
        sender=bidder.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[b"bid"],
        foreign_assets=[nftID],
        # must include the previous lead bidder here to the app can refund that bidder's payment
        accounts=[prevBidLeader] if prevBidLeader is not None else [],
        sp=suggestedParams,
    )

    transaction.assign_group_id([payTxn, appCallTxn])

    signedPayTxn = payTxn.sign(bidder.getPrivateKey())
    signedAppCallTxn = appCallTxn.sign(bidder.getPrivateKey())

    client.send_transactions([signedPayTxn, signedAppCallTxn])

    waitForTransaction(client, appCallTxn.get_txid())


def closeAuction(client: AlgodClient, appID: int, closer: Account):
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