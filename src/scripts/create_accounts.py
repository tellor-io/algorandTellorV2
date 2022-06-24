from algosdk import account
from algosdk import mnemonic
from algosdk.future.transaction import Multisig


def create_accounts():
    """
    Prints to terminal new addresses,
    accounts, and mnemonics (private keys) for...
    - two multis signers
    - a multisig with the two signers
    - a reporter
    """

    accounts = ["multis1", "multis2"]
    multisig_accounts_pk = []

    for i in accounts:

        private_key, public_address = account.generate_account()
        multisig_accounts_pk.append(public_address)

        print("{} Public Key: {}\n".format(i, public_address))

        print(f"{i} Mnemonic: ", mnemonic.from_private_key(private_key), "\n")

    governance = Multisig(version=1, threshold=2, addresses=multisig_accounts_pk)

    reporter_private_key, reporter_public_address = account.generate_account()

    print("reporter mnemonic: ", mnemonic.from_private_key(reporter_private_key))
    print("reporter address: ", reporter_public_address, "\n")

    print("Multisig address: ", governance.address())


create_accounts()
