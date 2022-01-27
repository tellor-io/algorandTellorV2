from pyteal import *
import pyteal

staking_token_id = App.globalGet(Bytes("staking_token_id"))

is_tipper = Txn.sender() == App.globalGet(Bytes("tipper"))
num_reports = Bytes("num_reports")
stake_amount = Bytes("stake_amount")


#TODO dispute statuses
def create():
        '''
        args:
        0) governance address
        1) query id
        2) query data

        maybe...:
        - add expiration
        '''
        return Seq([
            App.globalPut(Bytes("tipper"), Txn.sender()),
            #TODO assert application args length is correct
            Assert(Txn.application_args.length() == Int(3)),
            App.globalPut(Bytes("governance_address"), Txn.application_args[0]),
            App.globalPut(Bytes("query_id"), Txn.application_args[1]),
            App.globalPut(Bytes("query_data"), Txn.application_args[2]), #TODO perhaps parse from ipfs
            # 0-not Staked, 1=Staked
            App.globalPut(Bytes("staking_status"), Int(0)),
            App.globalPut(num_reports, Int(0)),
            App.globalPut(stake_amount, Int(int(190 * 0.95 * 100000))), # 200 dollars of ALGO
            Approve(),
        ])

def stake():

        reporter_address = Gtxn[0].sender()

        reporter_algo_balance = Balance(
            reporter_address
        )

        #TODO two part Gtxn: 1) send token to contract, 2) stake
        return Seq([
            Assert(
                reporter_algo_balance > App.globalGet(stake_amount),
            ),
            App.globalPut(Bytes("currently_staked"), Int(1)),
            App.globalPut(Bytes("reporter_address"), reporter_address),
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
                App.globalGet(Bytes("query_id")) == Txn.application_args[1]
            )
        ),
        App.globalPut(Bytes("query_id"), Txn.application_args[1]),
        App.globalPut(Bytes("query_data"), Txn.application_args[2]),
        App.globalPut(Bytes("value"), Txn.application_args[3]),
        Approve(),
    ])

def withdraw():
    #TODO finish withdraw
    '''
    corresponds to withdrawStake()

    '''
    return Seq([
        #assert the reporter is staked
        Assert(
            App.globalGet(Bytes("currently_staked")) == Int(1),
        ),
        #change staking status to unstaked
        App.globalPut(Bytes("currently_staked"), Int(0)),
        #send funds back to reporter (the sender) w/ inner tx
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.amount: App.globalGet(Bytes("stake_amount")),
            TxnField.receiver: App.globalGet(Bytes("reporter_address"))
        }),
        InnerTxnBuilder.Submit(),
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
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.amount: App.globalGet(Bytes("stake_amount")),
                    TxnField.receiver: App.globalGet(Bytes("governance_address")) #TODO can the receive be the contract itself?
                }),
                InnerTxnBuilder.Submit(),
                App.globalPut(Bytes("currently_staked"), Int(1)),
            ])

        def reward_reporter():
            '''increase reporter's number of recorded reports'''
            return App.globalPut(num_reports, App.globalGet(num_reports) + Int(1))


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
            [contract_method == Bytes("withdraw"), withdraw()]
        )

def close():
    return Seq([
        App.globalPut(Bytes("curently_staked"), Int(0)),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.amount: App.globalGet(Bytes("stake_amount")),
            TxnField.receiver: App.globalGet(Bytes("reporter_address"))
        }),
        InnerTxnBuilder.Submit(),
        Approve()
    ])