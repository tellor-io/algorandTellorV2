import json
from algosdk.v2client.algod import AlgodClient
from algosdk import encoding, mnemonic
from dotenv import load_dotenv
from src.utils.account import Account
import base64
import os
from algosdk.future.transaction import *

load_dotenv()

mnemonic1 = os.getenv("MNEMONIC1").replace(",", "")
mnemonic2 = os.getenv("MNEMONIC2").replace(",", "")
mnemonic3 = os.getenv("MNEMONIC3").replace(",", "")
mnemonic4 = os.getenv("MNEMONIC4").replace(",", "")

acc_1 = Account.FromMnemonic(mnemonic1)
acc_2 = Account.FromMnemonic(mnemonic2)
acc_3 = Account.FromMnemonic(mnemonic3)
acc_4 = Account.FromMnemonic(mnemonic4)

# create a multisig account
version = 1  # multisig version
threshold = 3  # how many signatures are necessary
msig = Multisig(version, threshold, [acc_1.addr, acc_2.addr, acc_3.addr])

print("Multisig Address: ", msig.address())
print('Go to the below link to fund the created account using testnet faucet: \n https://dispenser.testnet.aws.algodev.network/?account={}'.format(msig.address())) 

