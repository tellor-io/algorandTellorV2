from pyteal import *

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
medianizer = Bytes("medianizer")
is_governance = Txn.sender() == App.globalGet(governance_address)
is_reporter = Txn.sender() == App.globalGet(reporter)

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
    3) medianizer application address

    """
    return Seq(
        [
            App.globalPut(tipper, Txn.sender()),
            App.globalPut(tip_amount, Int(0)),
            App.globalPut(governance_address, Txn.application_args[0]),
            App.globalPut(query_id, Txn.application_args[1]),
            App.globalPut(query_data, Txn.application_args[2]),
            App.globalPut(medianizer, Txn.application_args[3]),
            # 0-not Staked, 1=Staked
            App.globalPut(reporter, Bytes("")),
            App.globalPut(staking_status, Int(0)),
            App.globalPut(values, Bytes("base64", "")),
            App.globalPut(timestamps, Bytes("base64", "")),
            App.globalPut(stake_timestamp, Int(0)),
            App.globalPut(stake_amount, Int(200000)),  # 200 dollars of ALGO
            Approve(),
        ]
    )


def change_governance():
    """
    changes governance application id

    Txn args:
    0) will always equal "change_governance" (in order to route to this method)
    1) application id -- new governance application id
    """

    return Seq(
        [
            Assert(
                And(
                    is_governance,
                    Txn.application_args.length() == Int(2),
                )
            ),
            App.globalPut(governance_address, Txn.application_args[1]),
            Approve(),
        ]
    )


def change_medianizer():
    """
    changes medianizer application id

    Txn args:
    0) will always equal "change_medianizer" (in order to route to this method)
    1) application id -- new medianizer application id

    """
    return Seq(
        [
            Assert(
                And(
                    is_governance,
                    Txn.application_args.length() == Int(2),
                )
            ),
            App.globalPut(medianizer, Txn.application_args[1]),
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

    last_timestamp = ScratchVar(TealType.bytes)
    last_value = ScratchVar(TealType.bytes)

    def add_value():
        return Seq(
            [
                last_value.store(Txn.application_args[2]),
                If(
                    Len(App.globalGet(values)) + Int(6) >= Int(128) - Len(values),
                    Seq(
                        [
                            App.globalPut(values, Substring(App.globalGet(values), Int(6), Int(128))),
                            App.globalPut(values, Concat(App.globalGet(values), Txn.application_args[2])),
                        ]
                    ),
                    App.globalPut(values, Concat(App.globalGet(values), Txn.application_args[2])),
                ),
            ]
        )

    def add_timestamp():
        return Seq(
            [
                last_timestamp.store(Txn.application_args[3]),
                If(
                    Len(App.globalGet(timestamps)) + Int(6) >= Int(128) - Len(timestamps),
                    Seq(
                        [
                            App.globalPut(timestamps, Substring(App.globalGet(timestamps), Int(6), Int(128))),
                            App.globalPut(timestamps, Concat(App.globalGet(timestamps), Txn.application_args[3])),
                        ]
                    ),
                    App.globalPut(timestamps, Concat(App.globalGet(timestamps), Txn.application_args[3])),
                ),
            ]
        )

    def get_last_timestamp():
        return Seq(
            [
                If(
                    App.globalGet(timestamps) == Bytes(""),
                    last_timestamp.store(Bytes("0")),
                    last_timestamp.store(
                        Substring(
                            App.globalGet(timestamps),
                            Len(App.globalGet(timestamps)) - Int(6),
                            Len(App.globalGet(timestamps)),
                        )
                    ),
                )
            ]
        )

    def get_last_value():
        return Seq(
            [
                If(
                    App.globalGet(values) == Bytes(""),
                    last_value.store(Bytes("0")),
                    last_value.store(
                        Substring(
                            App.globalGet(values), Len(App.globalGet(values)) - Int(6), Len(App.globalGet(values))
                        )
                    ),
                )
            ]
        )

    medianizer_query_id = App.globalGetEx(Int(1), query_id)

    return Seq(
        [
            medianizer_query_id,
            Assert(
                And(
                    Txn.applications[1] == App.globalGet(medianizer),
                    medianizer_query_id.hasValue(),
                    App.globalGet(query_id) == medianizer_query_id.value(),
                    App.globalGet(reporter) == Txn.sender(),
                    App.globalGet(staking_status) == Int(1),
                    App.globalGet(query_id) == Txn.application_args[1],
                )
            ),
            get_last_timestamp(),
            # App.globalPut(values, Txn.application_args[2]),
            # App.globalPut(timestamps, Int(int(time.time()))),
            add_value(),
            add_timestamp(),
            App.globalPut(Bytes("last_value"), Concat(last_timestamp.load(), last_value.load())),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.ApplicationCall,
                    TxnField.application_id: App.globalGet(medianizer),
                    TxnField.application_args: [Bytes("get_values")],
                    TxnField.applications: [
                        Txn.applications[1],
                        Txn.applications[2],
                        Txn.applications[3],
                        Txn.applications[4],
                        Txn.applications[5],
                    ],
                }
            ),
            InnerTxnBuilder.Submit(),
            InnerTxnBuilder.Begin(),
            # 98% goes to reporter
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.amount: Div(Mul(App.globalGet(tip_amount), Int(98)), Int(100)),
                    TxnField.receiver: Txn.sender(),
                }
            ),
            # 2% fee to governance
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.amount: Div(Mul(App.globalGet(tip_amount), Int(2), Int(100))),
                    TxnField.receiver: Txn.sender(),
                }
            ),
            InnerTxnBuilder.Submit(),
            App.globalPut(App.globalGet(tip_amount), Int(0)),
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
            # App.globalPut(stake_timestamp, Global.latest_timestamp()),
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

    return Seq(
        [
            Assert(
                And(
                    Gtxn[on_stake_tx_index].sender() == Txn.sender(),
                    Gtxn[on_stake_tx_index].receiver() == Global.current_application_address(),
                    Gtxn[on_stake_tx_index].type_enum() == TxnType.Payment,
                ),
            ),
            App.globalPut(tip_amount, App.globalGet(tip_amount) + Gtxn[on_stake_tx_index].amount()),
            Approve(),
        ]
    )


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
            Assert(
                And(
                    is_reporter,
                    Global.latest_timestamp() - App.globalGet(stake_timestamp)
                    > Int(604800),  # assert the reporter's stake has been locked for 7 days since withdrawal request
                    App.globalGet(staking_status) == Int(2),
                )
            ),
            # change locked status to unstaked
            App.globalPut(staking_status, Int(0)),
            App.globalPut(stake_timestamp, Int(0)),
            # send funds back to reporter (the sender) w/ inner tx
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.Payment,
                    # TxnField.amount: App.globalGet(stake_amount),
                    TxnField.close_remainder_to: App.globalGet(reporter),
                    # TxnField.applications: Txn.applications,
                }
            ),
            InnerTxnBuilder.Submit(),
            Approve(),
        ]
    )


def withdraw_request():
    """
    reporter has to request withdrawal and
    lock their balance for 7 days
    before they can withdraw their stake

    Txn args:
    0) will always equal "withdraw_request"

    """
    return Seq(
        [
            Assert(
                And(
                    is_reporter,
                    App.globalGet(staking_status) == Int(1),  # is staked
                    App.globalGet(stake_timestamp) == Int(0),  # first time requesting to withdraw
                )
            ),
            App.globalPut(stake_timestamp, Global.latest_timestamp()),  # start staking time interval
            App.globalPut(staking_status, Int(2)),  # status = 2 means your stake is in a locked state for 7 days
            Approve(),
        ]
    )


def slash_reporter():
    """
    allows the governance contract to approve or deny a new value
    if governance approves, the num_votes counter increases by 1
    if governance rejects, the reporter's ALGO stake is sent to
    the governance contract

    solidity equivalent: slashMiner()

    Args:
    0) will always be equal to "slash_reporter"
    """

    return Seq(
        [
            Assert(is_governance),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.close_remainder_to: App.globalGet(governance_address),
                }
            ),
            InnerTxnBuilder.Submit(),
            App.globalPut(staking_status, Int(0)),
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
        [contract_method == Bytes("change_governance"), change_governance()],
        [contract_method == Bytes("stake"), stake()],
        [contract_method == Bytes("tip"), tip()],
        [contract_method == Bytes("report"), report()],
        [contract_method == Bytes("slash_reporter"), slash_reporter()],
        [contract_method == Bytes("withdraw"), withdraw()],
        [contract_method == Bytes("withdraw_request"), withdraw_request()],
    )
