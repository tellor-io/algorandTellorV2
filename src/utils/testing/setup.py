from typing import List
from typing import Optional

from algosdk.kmd import KMDClient
from algosdk.v2client.algod import AlgodClient

from src.utils.account import Account

ALGOD_ADDRESS = "http://localhost:4001"
ALGOD_TOKEN = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def getAlgodClient(network) -> AlgodClient:
    if network == "testnet":
        algo_address = "http://testnet-api.algonode.cloud"
        algo_token = ""
    elif network == "mainnet":
        algo_address = "http://mainnet-api.algonode.cloud"
        algo_token = ""
    else:
        algo_address = "http://localhost:4001"
        algo_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    return AlgodClient(algod_address=algo_address, algod_token=algo_token)


KMD_ADDRESS = "http://localhost:4002"
KMD_TOKEN = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def getKmdClient() -> KMDClient:
    return KMDClient(KMD_TOKEN, KMD_ADDRESS)


KMD_WALLET_NAME = "unencrypted-default-wallet"
KMD_WALLET_PASSWORD = ""

kmdAccounts: Optional[List[Account]] = None


def getGenesisAccounts() -> List[Account]:
    global kmdAccounts

    if kmdAccounts is None:
        kmd = getKmdClient()

        wallets = kmd.list_wallets()
        walletID = None
        for wallet in wallets:
            if wallet["name"] == KMD_WALLET_NAME:
                walletID = wallet["id"]
                break

        if walletID is None:
            raise Exception("Wallet not found: {}".format(KMD_WALLET_NAME))

        walletHandle = kmd.init_wallet_handle(walletID, KMD_WALLET_PASSWORD)

        try:
            addresses = kmd.list_keys(walletHandle)
            privateKeys = [kmd.export_key(walletHandle, KMD_WALLET_PASSWORD, addr) for addr in addresses]
            kmdAccounts = [Account(sk) for sk in privateKeys]
        finally:
            kmd.release_wallet_handle(walletHandle)

    return kmdAccounts
