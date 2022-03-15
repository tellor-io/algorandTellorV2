"""
This is a rough draft, everything is subject to change
Inspired by Tellorflex Governance

creator is multisig
"""

from pyteal import *

foreign_application_id = Bytes("foreign_application_id")
application_id = Txn.applications[1]
team_multisig = Bytes("team_multi_sig")
disputer = Bytes("disputer_addr")
dispute_fee = Bytes("dispute_fee")
dispute_start_time = Bytes("dispute_start_time")
dispute_end_date = Bytes("dispute_end_date")
vote_count = Bytes("vote_count")
dispute_query_id = Bytes("dispute_query_id")
dispute_timestamp = Bytes("dispute_timestamp")
contract_address = Bytes("contract_address") # feed address to be disputed
is_team_multisig = Txn.sender() == App.globalGet(team_multisig)

get_timestamp = App.globalGetEx(application_id, Bytes("timestamps"))
get_values = App.globalGetEx(application_id, Bytes("values"))
get_query_id = App.globalGetEx(application_id, Bytes("query_id"))
get_reporter = App.globalGetEx(application_id, Bytes("reporter"))

def create():
    """
    constructor
    -algorand tellorflex contract Id (has to the first application id in applications array during deployment)
    -team multisig address
    -dispute fee

    """
    return Seq(
        [
            App.globalPut(team_multisig, Txn.sender()),
            App.globalPut(dispute_fee, Txn.application_args[1]),
            App.globalPut(foreign_application_id, Txn.application_args[2]),
            App.globalPut(disputer, Bytes("")),
            App.globalPut(Bytes("vote_decision"), Int(3)),
            Approve(),
        ]
    )

def begin_dispute():
    """
    To begin dispute you need to input
    query_id and timestamp
    
    """
    # ensure feed exits, check timestamp that it hasn't passed
    # globalGetEx(feed, timestamp)
    # remember you have timestamp with each report
    on_stake_tx_index = Txn.group_index() - Int(1)

    return Seq([# gets query_ids, timestamps, and values from tellorflex
        get_query_id,
        get_timestamp,
        get_values,
        Assert(
            And(
                Txn.application_args.length() == Int(2),
                App.globalGet(disputer) == Bytes(""),
                # checks if there are values in tellorflex 
                get_query_id.hasValue(),
                get_timestamp.hasValue(),
                get_values.hasValue(),
                # take dispute fee
                Gtxn[on_stake_tx_index].sender() == Txn.sender(),
                Gtxn[on_stake_tx_index].receiver() == Global.current_application_address(),
                Gtxn[on_stake_tx_index].amount() == App.globalGet(dispute_fee),
                Gtxn[on_stake_tx_index].type_enum() == TxnType.Payment
            )),
            #TODO: check if query_id and timestamp match with global values

        
        App.globalPut(dispute_start_time, Global.latest_timestamp()),
        App.globalPut(disputer, Gtxn[on_stake_tx_index].sender()),
        App.globalPut(dispute_query_id, Txn.application_args[1]),
        App.globalPut(dispute_timestamp, Txn.application_args[2]),

        Approve()
    ]
    )
   
def execute_vote():
    """
    If vote == 1 give dispute fee to reporter
    If vote == 0 give reporter stake to disputer
    """
    vote = App.globalGet(Bytes("vote_decision"))
    def pay_reporter():
        pass
    def pay_disputer():
        pass
    return Seq([
        Assert(
            And(
                is_team_multisig,
                # vote_has_ended,

            )
        ),
        InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.ApplicationCall,
            TxnField.application_id: App.globalGet(foreign_application_id),
            TxnField.application_args: [Bytes("vote"),vote]}),
        InnerTxnBuilder.Submit(),
        Approve()
     ] )

def tallyVotes():
    pass

def Vote():
    pass

def propose_change_governance_address():
    pass

def proposeChangeReportingLock():
    pass

def proposeChangeStakeAmount():
    pass

def handle_method():
    """
    calls the appropriate contract method if
    a NoOp transaction is sent to the contract
    """
    contract_method = Txn.application_args[0]
    return Cond(
        [contract_method == Bytes("begin_dispute"), begin_dispute()],
        [contract_method == Bytes("execute_vote"), execute_vote()],
    )