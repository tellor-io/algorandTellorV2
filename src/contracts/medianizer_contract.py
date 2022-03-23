from pyteal import *

"""
Medianizer for feed i.e. BTC/USD

"""

time_interval = Bytes("time_interval")
median_timestamp = Bytes("median_timestamp")
median_price = Bytes("median")
app_1 = Bytes("app_1")
app_2 = Bytes("app_2")
app_3 = Bytes("app_3")
app_4 = Bytes("app_4")
app_5 = Bytes("app_5")

# this is the name of variable in feed contract to read from
last_value = Bytes("last_value")

governance = Bytes("governance")
is_governance = Txn.sender() == App.globalGet(governance)
is_valid_feed = Btoi(Txn.sender()) == Or(
    Btoi(App.globalGet(app_1)),
    Btoi(App.globalGet(app_2)),
    Btoi(App.globalGet(app_3)),
    Btoi(App.globalGet(app_4)),
    Btoi(App.globalGet(app_5)),
)



def create():
    """
    constructor for medianizer contract

    args:
    0) governance address
    1) time interval that checks age of values

    """
    return Seq(
        App.globalPut(governance, Txn.application_args[1]),
        App.globalPut(time_interval, Txn.application_args[2]),
        Approve(),
    )


def activate_contract():
    """
    Only governance sets the application(aka feed) ids
    that are able to use this medianizer

    Txn args:
    0) will always equal "activate_contract"

    """
    addr_1 = AppParam.address(Int(1))
    addr_2 = AppParam.address(Int(2))
    addr_3 = AppParam.address(Int(3))
    addr_4 = AppParam.address(Int(4))
    addr_5 = AppParam.address(Int(5))
    return Seq(
        Assert(is_governance),
        addr_1,
        addr_2,
        addr_3,
        addr_4,
        addr_5,
        App.globalPut(app_1, addr_1.value()),
        App.globalPut(app_2, addr_2.value()),
        App.globalPut(app_3, addr_3.value()),
        App.globalPut(app_4, addr_4.value()),
        App.globalPut(app_5, addr_5.value()),
        Approve(),
    )


def get_values():
    """
    Gets values and timestamp of last report from all feeds
    and checks timestamp age against time_interval then passes
    values to medinizer function to get the median and stores globally

    Txn args:
    0) will always equal "get_values"

    """

    feed_1_value = App.globalGetEx(Int(1), last_value)
    feed_2_value = App.globalGetEx(Int(2), last_value)
    feed_3_value = App.globalGetEx(Int(3), last_value)
    feed_4_value = App.globalGetEx(Int(4), last_value)
    feed_5_value = App.globalGetEx(Int(5), last_value)

    var1 = ScratchVar(TealType.uint64)
    var2 = ScratchVar(TealType.uint64)
    var3 = ScratchVar(TealType.uint64)
    var4 = ScratchVar(TealType.uint64)
    var5 = ScratchVar(TealType.uint64)

    validate_prices = Seq(
        If(
            And(
                feed_1_value.hasValue(),
                Minus(Btoi(Substring(feed_1_value.value(), Int(11), Int(20))), Global.latest_timestamp())
                > App.globalGet(time_interval),
            )
        )
        .Then(var1.store(Btoi(Substring(feed_1_value.value(), Int(1), Int(10)))))
        .Else(var1.store(Int(0))),
        If(
            And(
                feed_2_value.hasValue(),
                Minus(Btoi(Substring(feed_2_value.value(), Int(11), Int(20))), Global.latest_timestamp())
                > App.globalGet(time_interval),
            )
        )
        .Then(var2.store(Btoi(Substring(feed_2_value.value(), Int(1), Int(10)))))
        .Else(var2.store(Int(0))),
        If(
            And(
                feed_3_value.hasValue(),
                Minus(Btoi(Substring(feed_3_value.value(), Int(11), Int(20))), Global.latest_timestamp())
                > App.globalGet(time_interval),
            )
        )
        .Then(var3.store(Btoi(Substring(feed_3_value.value(), Int(1), Int(10)))))
        .Else(var3.store(Int(0))),
        If(
            And(
                feed_4_value.hasValue(),
                Minus(Btoi(Substring(feed_4_value.value(), Int(11), Int(20))), Global.latest_timestamp())
                > App.globalGet(time_interval),
            )
        )
        .Then(var4.store(Btoi(Substring(feed_4_value.value(), Int(1), Int(10)))))
        .Else(var4.store(Int(0))),
        If(
            And(
                feed_5_value.hasValue(),
                Minus(Btoi(Substring(feed_5_value.value(), Int(11), Int(20))), Global.latest_timestamp())
                > App.globalGet(time_interval),
            )
        )
        .Then(var5.store(Btoi(Substring(feed_5_value.value(), Int(1), Int(10)))))
        .Else(var5.store(Int(0))),
    )

    return Seq(
        Assert(is_valid_feed),
        feed_1_value,
        feed_2_value,
        feed_3_value,
        feed_4_value,
        feed_5_value,
        validate_prices,
        App.globalPut(median_price, Medianizer(var1.load(), var2.load(), var3.load(), var4.load(), var5.load())),
        If(App.globalGet(median_price) == var1.load())
        .Then(App.globalPut(median_timestamp, Btoi(Substring(feed_1_value.value(), Int(11), Int(20)))))
        .ElseIf(App.globalGet(median_price) == var2.load())
        .Then(App.globalPut(median_timestamp, Btoi(Substring(feed_2_value.value(), Int(11), Int(20)))))
        .ElseIf(App.globalGet(median_price) == var3.load())
        .Then(App.globalPut(median_timestamp, Btoi(Substring(feed_3_value.value(), Int(11), Int(20)))))
        .ElseIf(App.globalGet(median_price) == var4.load())
        .Then(App.globalPut(median_timestamp, Btoi(Substring(feed_4_value.value(), Int(11), Int(20)))))
        .ElseIf(App.globalGet(median_price) == var5.load())
        .Then(App.globalPut(median_timestamp, Btoi(Substring(feed_5_value.value(), Int(11), Int(20))))),
        Approve(),
    )


@Subroutine(TealType.uint64)
def Medianizer(a: Expr, b: Expr, c: Expr, d: Expr, e: Expr) -> TealType.uint64:
    """
    function for getting the middle value

    sorts values one at a time
    until all values are sorted

    if number of values is odd, middle num is picked
    else divides middle two values and divides by 2
    """

    tmp = ScratchVar(TealType.uint64)

    sort_1 = Seq(
        tmp.store(a),
        If(And(b > a, b > c, b > d, b > e))
        .Then(Seq(a.slot.store(b), b.slot.store(tmp.load())))
        .ElseIf(And(c > b, c > a, c > d, c > e))
        .Then(Seq(a.slot.store(c), c.slot.store(tmp.load())))
        .ElseIf(And(d > b, d > a, d > c, d > e))
        .Then(Seq(a.slot.store(d), d.slot.store(tmp.load())))
        .ElseIf(And(e > b, e > a, e > c, e > d))
        .Then(Seq(a.slot.store(e), e.slot.store(tmp.load()))),
    )

    sort_2 = Seq(
        tmp.store(b),
        If(And(c > b, c > d, c > e))
        .Then(Seq(b.slot.store(c), c.slot.store(tmp.load())))
        .ElseIf(And(d > b, d > c, d > e))
        .Then(Seq(b.slot.store(d), d.slot.store(tmp.load())))
        .ElseIf(And(e > b, e > c, e > d))
        .Then(Seq(b.slot.store(e), e.slot.store(tmp.load()))),
    )
    sort_3 = Seq(
        tmp.store(c),
        If(And(d > c, d > e))
        .Then(Seq(c.slot.store(d), d.slot.store(tmp.load())))
        .ElseIf(And(e > c, e > d))
        .Then(Seq(c.slot.store(e), e.slot.store(tmp.load()))),
    )

    sort_4 = Seq(tmp.store(d), If(e > d).Then(Seq(d.slot.store(e), e.slot.store(tmp.load()))))

    i = ScratchVar(TealType.uint64)
    value_count = Seq(
        i.store(Int(0)),
        If(a > Int(0), i.store(i.load() + Int(1))),
        If(b > Int(0), i.store(i.load() + Int(1))),
        If(c > Int(0), i.store(i.load() + Int(1))),
        If(d > Int(0), i.store(i.load() + Int(1))),
        If(e > Int(0), i.store(i.load() + Int(1))),
    )

    middle_value = Seq(
        If(i.load() == Int(5))
        .Then(c.slot.load())
        .ElseIf(i.load() == Int(4))
        .Then(Div((b.slot.load() + c.slot.load()), Int(2)))
        .ElseIf(i.load() == Int(3))
        .Then(b.slot.load())
        .ElseIf(i.load() == Int(2))
        .Then(Div((a.slot.load() + b.slot.load()), Int(2)))
        .ElseIf(i.load() == Int(1))
        .Then(a.slot.load())
        .Else(Int(1))
    )
    return Seq(sort_1, sort_2, sort_3, sort_4, value_count, middle_value)


def handle_method():
    """
    calls the appropriate contract method if
    a NoOp transaction is sent to the contract
    """
    contract_method = Txn.application_args[0]
    return Cond(
        [contract_method == Bytes("activate_contract"), activate_contract()],
        [contract_method == Bytes("get_values"), get_values()],
    )
