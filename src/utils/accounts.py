from src.utils.testing.resources import getTemporaryAccount


class Accounts:
    def __init__(self, client) -> None:
        self.tipper = getTemporaryAccount(client)
        self.reporter = getTemporaryAccount(client)
        self.governance = getTemporaryAccount(client)
        self.bad_actor = getTemporaryAccount(client)
