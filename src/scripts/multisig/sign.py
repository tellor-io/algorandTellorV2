import json
from algosdk.v2client.algod import AlgodClient
from algosdk import encoding, mnemonic
from dotenv import load_dotenv
from src.utils.account import Account
import base64
import os
from algosdk.future.transaction import *

load_dotenv()

multis_mnemonic = os.getenv("MULTIS_MNEMONIC").replace(",", "")
recipient_mnemonic = os.getenv("MNEMONIC4").replace(",", "")

acc = Account.FromMnemonic(multis_mnemonic)
msig = Multisig.get_multisig_account("M2GCDVDLWSXFQMPJDD52MLHCR52XFTEFMRX5T2PRUYURE5LW4LNYWXG6ZU")

# sandbox
algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

# Initialize an algod client
algod_client = AlgodClient(algod_token, algod_address)
params = algod_client.suggested_params()

# create a transaction
recipient = Account.FromMnemonic(recipient_mnemonic)
amount = 10000
note = "Team Multisig".encode()
txn = PaymentTxn(msig, params, recipient.addr, amount, None, note, None)

# create a SignedTransaction object
mtx = MultisigTransaction(txn, msig)

# sign the transaction
mtx.sign(acc.getPrivateKey())

try:
# send the transaction
    txid = algod_client.send_raw_transaction(
    encoding.msgpack_encode(mtx))    
    print("TXID: ", txid)   
    confirmed_txn = wait_for_confirmation(algod_client, txid, 6)  
    print("Result confirmed in round: {}".format(confirmed_txn['confirmed-round']))
    print("Transaction information: {}".format(
        json.dumps(confirmed_txn, indent=4)))
    print("Decoded note: {}".format(base64.b64decode(
        confirmed_txn["txn"]["txn"]["note"]).decode()))
except Exception as err:
    print(err)