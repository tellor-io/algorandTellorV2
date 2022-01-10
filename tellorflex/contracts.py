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

    on_create = Seq([

        App.globalPut(Bytes("tipper"), Txn.sender()),
        #TODO assert application args length is correct
        Assert(Txn.application_args.length() == 3),
        App.globalPut(Bytes("governance_address"), Txn.application_args[0]),
        App.globalPut(Bytes("staking_token_address"), Txn.application_args[1]),
        App.globalPut(Bytes("stake_amount"), Txn.application_args[2]),
        Return(Int(1)),

        '''

        args:
        0 - governance address
        1 - stake amount

        maybe...:
        - add expiration
        - hardcode stake amount
        '''

    ])

    staking_token_address = App.globalGet("staking_token_address")

    on_stake = Seq([
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: staking_token_address,
            TxnField.asset_receiver: Global.current_application_address()
        }),
        InnerTxnBuilder.Submit(),
        Approve(),
    ])

    is_tipper = Txn.sender() == App.globalGet(Bytes("tipper"))

    contract_method = Txn.application_args[0]
    on_call = Cond(
        [contract_method == Bytes("report"), on_report],
        [contract_method == Bytes("vote"), on_vote],
    )


    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp, on_call],
        [Txn.on_completion() == OnComplete.OptIn, on_stake]
        [Txn.on_completion() == OnComplete.DeleteApplication, Return(is_creator)],
        [Txn.on_completion() == OnComplete.UpdateApplication, Return(is_creator)],
        [Txn.on_completion() == OnComplete.CloseOut, on_closeout]
    )

    return program
