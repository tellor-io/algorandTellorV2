from pyteal import *

def approval_program():

    '''
    - tipper creates contract
    - tipper initializes stake amount
    - tipper deploys
    - reporter stakes
    - reporter points to new address
    - reporter reports
    - tipper (ideally governance?) approves or rejects report
    - contract sends reward to reporter
    - governance can slash a reporter/report
    '''

    #state variables initialized to placeholders
    # token_address = Bytes("base32", "token address") #we might use algo token natively
    governance_address = Bytes("base32", "governance address") 
    stake_amount = Int(0) #amount required to be a staker
    # total_stake_amount = Int(0) #total amount of tokens locked in contract (via stake)
    # reporting_lock = Int(0) #base amount of time before a reporter is able to submit a value again
    # time_of_last_value = Int(0) #time of the last new submitted value, originally set to the block timestamp


    '''

    args:
    0) governance address
    1) stake amount

    maybe...:
    - add expiration
    - hardcode stake amount
    '''
    on_create = Seq([

        App.globalPut(Bytes("tipper"), Txn.sender()),
        #TODO assert application args length is correct
        Assert(Txn.application_args.length() == 3),
        App.globalPut(Bytes("governance_address"), Txn.application_args[0]),
        App.globalPut(Bytes("staking_token_address"), Txn.application_args[1]),
        App.globalPut(Bytes("stake_amount"), Txn.application_args[2]),
        App.globalPut(Bytes("query_id"), Txn.application_args[3]),
        App.globalPut(Bytes("query_data"), Txn.application_args[4]), #TODO perhaps parse from ipfs
        App.globalPut(Bytes("currently_staked"), Int(0)),
        Return(Int(1)),
    ])

    staking_token_address = App.globalGet("staking_token_address")

    on_stake = Seq([
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: staking_token_address,
            TxnField.asset_amount: 100,
            TxnField.asset_receiver: Global.current_application_address()
        }),
        InnerTxnBuilder.Submit(),
        App.globalPut(Bytes("reporter_address"), Txn.sender()),
        App.globalPut(Bytes("currently_staked"), Int(1)),
        Approve(),
        
    ])

    '''
    corresponds to submitValue()

    Txn args:
    0) will always equal "report" (in order to route to this method)
    1) query_id -- the ID of the data requested to be put on chain
    2) query_data -- the in-depth specifications of the data requested
    3) value -- the data submitted to the query
    '''
    on_report = Seq([
        Assert(
            App.globalGet("currently_staked") == Int(1),
            App.globalGet("query_id") == Txn.application_args()[1],
            AssetHolding.balance(
                Txn.sender(),
                staking_token_address
            ) >= App.globalGet(Bytes("stake_amount"))
        ),
        App.globalPut(Bytes("query_id"), Txn.application_args()[1]),
        App.globalPut(Bytes("query_data"), Txn.application_args()[2]),
        App.globalPut(Bytes("value"), Txn.application_args()[3]),
        Approve(),
    ])

    is_tipper = Txn.sender() == App.globalGet(Bytes("tipper"))

    def slash_reporter():
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: staking_token_address,
            TxnField.asset_amount: App.globalGet(Bytes("stake_amount")),
            TxnField.asset_receiver: Global.current_application_address()
        }),
        InnerTxnBuilder.Submit(),
        App.globalPut(Bytes("currently_staked"), Int(1)),

    def reward_reporter():
        return Seq([
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: staking_token_address,
            TxnField.asset_amount: App.globalGet(Bytes("stake_amount")),
            TxnField.asset_receiver: App.globalGet(Bytes("governance_address"))
        }),
        InnerTxnBuilder.Submit(),
        ])
    '''
    Args:
    0) will always be equal to "vote"
    1) decision -- 1 is approval, 0 is rejection, which slashes the miner
    '''
    on_vote = Seq([
        Assert(is_tipper),
        If(
            Txn.application_args()[1] == Int(1),
            reward_reporter(),
            slash_reporter()
        ),
        Approve(),
    ])

    contract_method = Txn.application_args[0]
    on_call = Cond(
        [contract_method == Bytes("report"), on_report],
        [contract_method == Bytes("vote"), on_vote],
    )

    on_closeout = Seq([
        App.globalPut(Bytes("curently_staked"), Int(0)),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: staking_token_address,
            TxnField.asset_amount: App.globalGet(Bytes("stake_amount")),
            TxnField.asset_receiver: App.globalGet(Bytes("reporter_address"))
        }),
        InnerTxnBuilder.Submit(),
    ])


    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp, on_call],
        [Txn.on_completion() == OnComplete.OptIn, on_stake]
        [Txn.on_completion() == OnComplete.DeleteApplication, Return(is_tipper)],
        [Txn.on_completion() == OnComplete.UpdateApplication, Return(is_tipper)],
        [Txn.on_completion() == OnComplete.CloseOut, on_closeout]
    )

    return program
