from pyteal import *

staking_token_address = App.globalGet("staking_token_address")

is_tipper = Txn.sender() == App.globalGet(Bytes("tipper"))

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
            Assert(Txn.application_args.length() == 3),
            App.globalPut(Bytes("governance_address"), Txn.application_args[0]),
            App.globalPut(Bytes("staking_token_address"), Txn.application_args[1]),
            App.globalPut(Bytes("stake_amount"), Txn.application_args[2]),
            App.globalPut(Bytes("query_id"), Txn.application_args[3]),
            App.globalPut(Bytes("query_data"), Txn.application_args[4]), #TODO perhaps parse from ipfs
            App.globalPut(Bytes("currently_staked"), Int(0)),
            Return(Int(1)),
        ])

def stake():
        return Seq([
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
            If(
                Txn.application_args()[1] == Int(1),
                reward_reporter(),
                slash_reporter()
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
    ])