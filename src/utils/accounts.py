from algosdk.future.transaction import Multisig

from src.utils.testing.resources import fundAccount
from src.utils.testing.resources import getTemporaryAccount


class Accounts:
    def __init__(self, client) -> None:
        self.tipper = getTemporaryAccount(client)
        self.reporter = getTemporaryAccount(client)
        self.bad_actor = getTemporaryAccount(client)
        self.multisig_obj = [getTemporaryAccount(client) for i in range(3)]
        self.multisig_signers = [i.getAddress() for i in self.multisig_obj]
        self.multisig_signers_sk = [i.getPrivateKey() for i in self.multisig_obj]
        self.governance = Multisig(version=1, threshold=2, addresses=self.multisig_signers)
