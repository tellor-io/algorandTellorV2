from pyteal import *
import pyteal

staking_token_address = App.globalGet(Bytes("staking_token_address"))

is_tipper = Txn.sender() == App.globalGet(Bytes("tipper"))

#TODO dispute statuses
def create():
        '''
        args:
        0) governance address
        1) staking-token address
        2) stake amount
        3) query id
        4) query data

        maybe...:
        - add expiration
        - hardcode stake amount
        '''
        return Seq([
            App.globalPut(Bytes("tipper"), Txn.sender()),
            #TODO assert application args length is correct
            Assert(Txn.application_args.length() == Int(5)),
            App.globalPut(Bytes("governance_address"), Txn.application_args[0]),
            App.globalPut(Bytes("staking_token_id"), Txn.application_args[1]), #TODO rename to asset id
            App.globalPut(Bytes("stake_amount"), Txn.application_args[2]),
            App.globalPut(Bytes("query_id"), Txn.application_args[3]),
            App.globalPut(Bytes("query_data"), Txn.application_args[4]), #TODO perhaps parse from ipfs
            App.globalPut(Bytes("currently_staked"), Int(0)),
            Approve(),
        ])

def stake():
        #TODO send ASA funds to contract in separate transaction
        return Seq([
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: staking_token_address,
                TxnField.asset_amount: Int(100), #TODO change to stake amount
                TxnField.asset_receiver: Global.current_application_address()
            }),
            InnerTxnBuilder.Submit(),
            #TODO fail if not empty
            App.globalPut(Bytes("reporter_address"), Txn.sender()),
            App.globalPut(Bytes("currently_staked"), Int(1)),
            Approve(),
            
        ])

def report():
    '''
    corresponds to submitValue()

    Txn args:
    0) will always equal "report" (in order to route to this method)
    1) query_id -- the ID of the data requested to be put on chain
    2) query_data -- the in-depth specifications of the data requested
    3) value -- the data submitted to the query
    '''
    return Seq([
        Assert(
            And(
                #TODO assert that the reporter is tx.sender()
                App.globalGet(Bytes("currently_staked")) == Int(1),
                App.globalGet(Bytes("query_id")) == Txn.application_args[1],
                # AssetHolding.balance(
                #     Txn.sender(),
                #     staking_token_address
                # ).hasValue(),
                # AssetHolding.balance(
                #     Txn.sender(),
                #     staking_token_address #TODO how to check balance of ASA at the staking token address?
                # ).value() >= App.globalGet(Bytes("stake_amount"))
            )
        ),
        App.globalPut(Bytes("query_id"), Txn.application_args[1]),
        App.globalPut(Bytes("query_data"), Txn.application_args[2]),
        App.globalPut(Bytes("value"), Txn.application_args[3]),
        Approve(),
    ])


def vote():
        '''
        Args:
        0) will always be equal to "vote"
        1) decision -- 1 is approval, 0 is rejection, which slashes the miner
        '''
        def slash_reporter():
            return Seq([
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields({
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: staking_token_address,
                    TxnField.asset_amount: App.globalGet(Bytes("stake_amount")),
                    TxnField.asset_receiver: Global.current_application_address()
                }),
                InnerTxnBuilder.Submit(),
                App.globalPut(Bytes("currently_staked"), Int(1)),
            ])

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

        return Seq([
            Assert(is_tipper),
            Cond(
                # [Txn.application_args[1].type_of() == TealType.uint64, Reject()],
                [Btoi(Txn.application_args[1]) == Int(1), reward_reporter()],
                [Btoi(Txn.application_args[1]) == Int(0), slash_reporter()]
            ),
            Approve(),
        ])

def handle_method():
        contract_method = Txn.application_args[0]
        return Cond(
            [contract_method == Bytes("report"), report()],
            [contract_method == Bytes("vote"), vote()],
        )

def close():
    return Seq([
        App.globalPut(Bytes("curently_staked"), Int(0)),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: staking_token_address,
            TxnField.asset_amount: App.globalGet(Bytes("stake_amount")),
            TxnField.asset_receiver: App.globalGet(Bytes("reporter_address"))
        }),
        InnerTxnBuilder.Submit(),
        Approve()
    ])