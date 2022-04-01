from src.utils.testing.resources import getTemporaryAccount
from algosdk.future.transaction import Multisig


class Accounts:
    def __init__(self, client) -> None:
        self.tipper = getTemporaryAccount(client)
        self.reporter = getTemporaryAccount(client)
        self.bad_actor = getTemporaryAccount(client)
        self.multisig_signers = [getTemporaryAccount(client) for i in range(3)]
        self.governance = Multisig(version=1,threshold=2,addresses=self.multisig_signers)
