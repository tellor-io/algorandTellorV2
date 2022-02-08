from pyteal import *
import pyteal

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
value = Bytes("value")

# currently staked vs staking status???



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
            App.globalPut(tipper, Txn.sender()),
            #TODO assert application args length is correct
            Assert(Txn.application_args.length() == Int(3)),
            App.globalPut(governance_address, Txn.application_args[0]),
            App.globalPut(query_id, Txn.application_args[1]),
            App.globalPut(query_data, Txn.application_args[2]), #TODO perhaps parse from ipfs
            # 0-not Staked, 1=Staked
            App.globalPut(reporter, Bytes("")),
            App.globalPut(staking_status, Int(0)),
            App.globalPut(num_reports, Int(0)),
            App.globalPut(stake_amount, Int(100000)), # 200 dollars of ALGO
            Approve(),
        ])

def stake():

        on_stake_tx_index = Txn.group_index() - Int(1)

        reporter_algo_balance = Balance(
            Gtxn[on_stake_tx_index].sender()
        )

        #TODO two part Gtxn: 1) send token to contract, 2) stake
        return Seq([
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
            App.globalPut(reporter, Gtxn[on_stake_tx_index].sender()),
            Approve(),
        ])

def report():
    '''
    corresponds to submitValue()

    Txn args:
    0) will always equal "report" (in order to route to this method)
    1) query_id -- the ID of the data requested to be put on chain
    2) value -- the data submitted to the query
    '''
    return Seq([
        Assert(
            And(
                #TODO assert that the reporter is tx.sender()
                App.globalGet(reporter) == Txn.sender(),
                App.globalGet(staking_status) == Int(1),
                App.globalGet(query_id) == Txn.application_args[1]
            )
        ),
        App.globalPut(value, Txn.application_args[2]),
        App.globalPut(num_reports, App.globalGet(num_reports) + Int(1)),
        Approve(),
    ])

def withdraw():
    #TODO finish withdraw
    '''
    corresponds to withdrawStake()

    '''
    return Seq([
        #TODO assert tx.sender is reporter
        #assert the reporter is staked
        Assert(
            And(
                Txn.sender() == App.globalGet(reporter),
                App.globalGet(staking_status) == Int(1),
            )
        ),
        #change staking status to unstaked
        App.globalPut(staking_status, Int(0)),
        #send funds back to reporter (the sender) w/ inner tx
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            # TxnField.amount: App.globalGet(stake_amount),
            TxnField.close_remainder_to: App.globalGet(reporter)
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
                    # TxnField.amount: App.globalGet(stake_amount),
                    TxnField.close_remainder_to: App.globalGet(governance_address) #TODO can the receive be the contract itself?
                }),
                InnerTxnBuilder.Submit(),
                App.globalPut(staking_status, Int(0)),
            ])

        def reward_reporter():
            '''increase reporter's number of recorded reports'''
            return App.globalPut(num_reports, App.globalGet(num_reports) + Int(1))


        return Seq([
            Assert(is_governance),
            Cond(
                [Or(
                    Btoi(Txn.application_args[1]) != Int(0),
                    Btoi(Txn.application_args[1]) != Int(1)
                ), 
                Reject()
                ],
                [Btoi(Txn.application_args[1]) == Int(1), reward_reporter()],
                [Btoi(Txn.application_args[1]) == Int(0), slash_reporter()]
            ),
            Approve(),
        ])

def handle_method():
        contract_method = Txn.application_args[0]
        return Cond(
            [contract_method == Bytes("stake"), stake()],
            [contract_method == Bytes("report"), report()],
            [contract_method == Bytes("vote"), vote()],
            [contract_method == Bytes("withdraw"), withdraw()],
        )

# def close():
#     return Seq([
#         App.globalPut(staking_status, Int(0)),
#         InnerTxnBuilder.Begin(),
#         InnerTxnBuilder.SetFields({
#             TxnField.type_enum: TxnType.Payment,
#             TxnField.amount: App.globalGet(stake_amount),
#             TxnField.receiver: App.globalGet(reporter)
#         }),
#         InnerTxnBuilder.Submit(),
#         Approve()
#     ])