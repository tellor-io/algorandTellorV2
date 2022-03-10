import time
from pyteal import *

staking_token_id = App.globalGet(Bytes("staking_token_id"))

is_governance = Txn.sender() == App.globalGet(Bytes("governance_address"))
num_reports = Bytes("num_reports")
stake_amount = Bytes("stake_amount")
governance_address = Bytes("governance_address")
query_id = Bytes("query_id")
query_data = Bytes("query_data")
staking_status = Bytes("staking_status")
tipper = Bytes("tipper")
reporter = Bytes("reporter_address")
currently_staked = Bytes("currently_staked")
timestamps = Bytes("timestamps")
values = Bytes("values")
tip_amount = Bytes("tip_amount")
stake_timestamp = Bytes("stake_timestamp")

"""
functions listed in alphabetical order

method arguments must be passed in provided order
as they are expected by the contract logic
to follow that order

for solidity equivalent reference contract, see
https://github.com/tellor-io/tellorFlex/blob/main/contracts/TellorFlex.sol
"""


def create():
    """
    does setup of Tellor contract on Alogrand
    solidity equivalent: constructor()

    args:
    0) governance address
    1) query id
    2) query data

    """
    return Seq(
        [
            App.globalPut(tipper, Txn.sender()),
            App.globalPut(tip_amount, Int(0)),
            # TODO assert application args length is correct
            App.globalPut(governance_address, Txn.application_args[0]),
            App.globalPut(query_id, Txn.application_args[1]),
            App.globalPut(query_data, Txn.application_args[2]),  # TODO perhaps parse from ipfs
            # 0-not Staked, 1=Staked
            App.globalPut(reporter, Bytes("")),
            App.globalPut(staking_status, Int(0)),
            App.globalPut(num_reports, Int(0)),
            App.globalPut(values, Bytes("base16", "")),
            App.globalPut(timestamps, Bytes("base16", "")),
            App.globalPut(stake_timestamp, Global.latest_timestamp()),
            App.globalPut(stake_amount, Int(200000)),  # 200 dollars of ALGO
            Approve(),
        ]
    )


def report():
    """
    changes the current value recorded in the contract
    solidity equivalent: submitValue()

    Txn args:
    0) will always equal "report" (in order to route to this method)
    1) query_id -- the ID of the data requested to be put on chain
    2) value -- the data submitted to the query
    3) timestamp -- the timestamp of the data submission
    """

    def add_value():
        return Seq([
            Assert(Len(Txn.application_args[2]) == Int(8)),
            If(Len(App.globalGet(values)) == Int(128),
            Seq([
                App.globalPut(values, Substring(App.globalGet(values), Int(8), Int(128))),
                App.globalPut(values, Concat(App.globalGet(values), Txn.application_args[2])),
            ]),
            App.globalPut(values, Concat(App.globalGet(values), Txn.application_args[2])),
            )
        ])
    def add_timestamp():
        return Seq([
        Assert(Len(Txn.application_args[3]) == Int(8)),
        If(Len(App.globalGet(timestamps)) == Int(128),
        Seq([
            App.globalPut(timestamps, Substring(App.globalGet(timestamps), Int(8), Int(128))),
            App.globalPut(timestamps, Concat(App.globalGet(timestamps), Txn.application_args[3])),
        ]),
        App.globalPut(timestamps, Concat(App.globalGet(timestamps), Txn.application_args[3]))
        )
        ])
    return Seq(
        [
            Assert(
                And(
                    App.globalGet(reporter) == Txn.sender(),
                    App.globalGet(staking_status) == Int(1),
                    App.globalGet(query_id) == Txn.application_args[1],
                )
            ),
            # App.globalPut(values, Txn.application_args[2]),
            # App.globalPut(timestamps, Int(int(time.time()))),

            add_value(),
            add_timestamp(),

            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.amount: App.globalGet(tip_amount),
                TxnField.receiver: Txn.sender()
            }),
            InnerTxnBuilder.Submit(),

            Approve(),
        ]
    )

def stake():
    """
    gives permission to reporter to report values
    changes permission when the contract
    receives the reporter's stake

    Args:
    0) will always be equal to "stake"
    """

    on_stake_tx_index = Txn.group_index() - Int(1)

    # enforced two part Gtxn: 1) send token to contract, 2) stake
    return Seq(
        [
            Assert(
                And(
                    App.globalGet(reporter) == Bytes(""),
                    Gtxn[on_stake_tx_index].sender() == Txn.sender(),
                    Gtxn[on_stake_tx_index].receiver() == Global.current_application_address(),
                    Gtxn[on_stake_tx_index].amount() == App.globalGet(stake_amount),
                    Gtxn[on_stake_tx_index].type_enum() == TxnType.Payment,
                ),
            ),
            App.globalPut(staking_status, Int(1)),
            App.globalPut(stake_timestamp, Global.latest_timestamp()),
            App.globalPut(reporter, Gtxn[on_stake_tx_index].sender()),
            Approve(),
        ]
    )

def tip():
    """
    provide a reward to the reporter for reporting

    Txn args:
    0) will always equal "tip" (in order to route to this method) 
    """
    on_stake_tx_index = Txn.group_index() - Int(1)

    return Seq([
        Assert(
            And(
                Gtxn[on_stake_tx_index].sender() == Txn.sender(),
                Gtxn[on_stake_tx_index].receiver() == Global.current_application_address(),
                Gtxn[on_stake_tx_index].type_enum() == TxnType.Payment,
            ),
        ),

        App.globalPut(tip_amount, App.globalGet(tip_amount) + Gtxn[on_stake_tx_index].amount())
    ])


def withdraw():
    """
    sends the reporter's stake back to their address
    removes their permission to report data

    solidity equivalent: withdrawStake()

    Txn args:
    0) will always equal "withdraw"

    """
    return Seq(
        [
            # assert the reporter is staked
            Assert(
                And(
                    Global.latest_timestamp() - App.globalGet(stake_timestamp) > Int(604800),
                    Txn.sender() == App.globalGet(reporter),
                    App.globalGet(staking_status) == Int(1),
                )
            ),
            # change staking status to unstaked
            App.globalPut(staking_status, Int(0)),
            # send funds back to reporter (the sender) w/ inner tx
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.Payment,
                    # TxnField.amount: App.globalGet(stake_amount),
                    TxnField.close_remainder_to: App.globalGet(reporter),
                }
            ),
            InnerTxnBuilder.Submit(),
            Approve(),
        ]
    )


def vote():
    """
    allows the governance contract to approve or deny a new value
    if governance approves, the num_votes counter increases by 1
    if governance rejects, the reporter's ALGO stake is sent to
    the governance contract

    solidity equivalent: slashMiner()

    Args:
    0) will always be equal to "vote"
    1) decision -- 1 is approval, 0 is rejection
    """

    def slash_reporter():
        """
        - transfers reporter's stake to governance contract
        - removes their permission to submit data (reporting)
        """
        return Seq(
            [
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.close_remainder_to: App.globalGet(governance_address),
                    }
                ),
                InnerTxnBuilder.Submit(),
                App.globalPut(staking_status, Int(0)),
            ]
        )

    def reward_reporter():
        """increase reporter's number of recorded reports"""
        return App.globalPut(num_reports, App.globalGet(num_reports) + Int(1))

    return Seq(
        [
            Assert(is_governance),
            Cond(
                [And(Btoi(Txn.application_args[1]) != Int(0), Btoi(Txn.application_args[1]) != Int(1)), Reject()],
                [Btoi(Txn.application_args[1]) == Int(1), reward_reporter()],
                [Btoi(Txn.application_args[1]) == Int(0), slash_reporter()],
            ),
            Approve(),
        ]
    )

def handle_method():
    """
    calls the appropriate contract method if
    a NoOp transaction is sent to the contract
    """
    contract_method = Txn.application_args[0]
    return Cond(
        [contract_method == Bytes("stake"), stake()],
        [contract_method == Bytes("report"), report()],
        [contract_method == Bytes("vote"), vote()],
        [contract_method == Bytes("withdraw"), withdraw()],
    )
