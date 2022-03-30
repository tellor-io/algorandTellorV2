import os
import sys
import base64
from dotenv import load_dotenv
from pyteal import Mode, compileTeal
from pyteal.compiler.compiler import MAX_TEAL_VERSION
from src.utils.configs import get_configs
from src.contracts.medianizer_contract import approval_program, clear_state_program
from src.utils.account import Account
from src.utils.testing.resources import fundAccount
from algosdk.v2client.algod import AlgodClient
from algosdk.future import transaction
from algosdk.future.transaction import Multisig, MultisigTransaction, encoding
from src.utils.testing.resources import getTemporaryAccount


def deploy(time_interval: int, network: str):

    load_dotenv()

    algo_address = "http://localhost:4001"
    algo_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    client = AlgodClient(algod_address=algo_address, algod_token=algo_token)

    print("current network: ", network)
    if network == "testnet":
        account_1 = Account.FromMnemonic(os.getenv("ACCOUNT_1"))
        account_2 = Account.FromMnemonic(os.getenv("ACCOUNT_2"))
    elif network == "devnet":
        account_1 = getTemporaryAccount(client)
        account_2 = getTemporaryAccount(client)
        msig = Multisig(version=1, threshold=2, addresses=[account_1.getAddress(), account_2.getAddress()])

        fundAccount(client, account_1.addr)
        fundAccount(client, account_2.addr)
        fundAccount(client, msig.address())
    else:
        raise Exception("invalid network selected")

    on_complete = transaction.OnComplete.NoOpOC.real

    # get node suggested parameters
    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = 1000

    global_schema = transaction.StateSchema(num_uints=7, num_byte_slices=6)
    local_schema = transaction.StateSchema(num_uints=0, num_byte_slices=0)

    def compile_program(client, source_code):
        compile_response = client.compile(source_code)
        return base64.b64decode(compile_response["result"])

    approval_state = approval_program()
    clear_state = clear_state_program()
    # compile program to TEAL assembly
    approval_program_teal = compileTeal(
        approval_state, mode=Mode.Application, version=MAX_TEAL_VERSION
    )
    clear_program_teal = compileTeal(
        clear_state, mode=Mode.Application, version=MAX_TEAL_VERSION
    )
    # compile program to binary
    approval_program_compiled = compile_program(client, approval_program_teal)
    clear_program_compiled = compile_program(client, clear_program_teal)

    app_args = [
        time_interval
    ]

    txn = transaction.ApplicationCreateTxn(
        sender=msig.address(),
        sp=params,
        on_complete=on_complete,
        approval_program=approval_program_compiled,
        clear_program=clear_program_compiled,
        global_schema=global_schema,
        local_schema=local_schema,
        app_args=app_args,
    )

    mtx = MultisigTransaction(txn, msig)

    # sign the transaction
    mtx.sign(account_1.getPrivateKey())
    mtx.sign(account_2.getPrivateKey())

    tx_id = client.send_raw_transaction(encoding.msgpack_encode(mtx))
    print("txn id: ", tx_id)
    # await confirmation
    last_round = client.status().get("last-round")
    txinfo = client.pending_transaction_info(tx_id)
    while not (txinfo.get("confirmed-round") and txinfo.get("confirmed-round") > 0):
        print("Waiting for confirmation...")
        last_round += 1
        client.status_after_block(last_round)
        txinfo = client.pending_transaction_info(tx_id)
    print(
        "Transaction {} confirmed in round {}.".format(
            tx_id, txinfo.get("confirmed-round")
        )
    )

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    app_id = transaction_response["application-index"]
    print("Created new app-id:", app_id)


config = get_configs(sys.argv[1:])
deploy(time_interval=config.time_interval, network=config.network)
