from pyteal import *

from .methods import *


def approval_program():

    """
    - tipper creates contract
    - tipper initializes stake amount
    - tipper deploys
    - reporter stakes
    - reporter points to new address
    - reporter reports
    - tipper (ideally governance?) approves or rejects report
    - contract sends reward to reporter
    - governance can slash a reporter/report
    """

    program = Cond(
        [Txn.application_id() == Int(0), create()],
        [Txn.on_completion() == OnComplete.NoOp, handle_method()],
        [Txn.on_completion() == OnComplete.DeleteApplication, Return(is_governance)],
        [Txn.on_completion() == OnComplete.UpdateApplication, Return(is_governance)],
        # [Txn.on_completion() == OnComplete.CloseOut, close()]
    )

    return program


def clear_state_program():
    return Approve()


if __name__ == "__main__":
    with open("auction_approval.teal", "w") as f:
        compiled = compileTeal(approval_program(), mode=Mode.Application, version=5)
        f.write(compiled)

    with open("auction_clear_state.teal", "w") as f:
        compiled = compileTeal(clear_state_program(), mode=Mode.Application, version=5)
        f.write(compiled)

    print("compiled!")
