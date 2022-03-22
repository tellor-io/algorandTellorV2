from pyteal import *

"""
Medianizer for feed i.e. BTC/USD

"""

time_interval = Bytes("time_interval")
median_timestamp = Int(0)
median_price = Bytes("median")

# TODO: ensure this is the name of variable in feed contract to read from
price = Bytes("price")

# TODO: Feed contract ids, application ids might not be necessary.

teamsig = Bytes("teamsig")
is_team = Txn.sender() == teamsig


def create():
    return Seq(
        [
            App.globalPut(teamsig, Txn.application_args[1]),
            App.globalPut(time_interval, Txn.application_args[2]),
            Approve(),
        ]
    )


@Subroutine(TealType.uint64)
def Medianizer(a: Expr, b: Expr, c: Expr, d: Expr, e: Expr):
    tmp = ScratchVar(TealType.uint64)

    sort_1 = Seq(
        [
            tmp.store(a),
            If(And(b > a, b > c, b > d, b > e))
            .Then(Seq(a.slot.store(b), b.slot.store(tmp.load())))
            .ElseIf(And(c > b, c > a, c > d, c > e))
            .Then(Seq(a.slot.store(c), c.slot.store(tmp.load())))
            .ElseIf(And(d > b, d > a, d > c, d > e))
            .Then(Seq(a.slot.store(d), d.slot.store(tmp.load())))
            .ElseIf(And(e > b, e > a, e > c, e > d))
            .Then(Seq(a.slot.store(e), e.slot.store(tmp.load()))),
        ]
    )

    sort_2 = Seq(
        [
            tmp.store(b),
            If(And(c > b, c > d, c > e))
            .Then(Seq(b.slot.store(c), c.slot.store(tmp.load())))
            .ElseIf(And(d > b, d > c, d > e))
            .Then(Seq(b.slot.store(d), d.slot.store(tmp.load())))
            .ElseIf(And(e > b, e > c, e > d))
            .Then(Seq(b.slot.store(e), e.slot.store(tmp.load()))),
        ]
    )
    sort_3 = Seq(
        [
            tmp.store(c),
            If(And(d > c, d > e))
            .Then(Seq(c.slot.store(d), d.slot.store(tmp.load())))
            .ElseIf(And(e > c, e > d))
            .Then(Seq(c.slot.store(e), e.slot.store(tmp.load()))),
        ]
    )

    sort_4 = Seq([tmp.store(d), If(e > d).Then(Seq(d.slot.store(e), e.slot.store(tmp.load())))])

    i = ScratchVar(TealType.uint64)
    x = Seq(
        [
            i.store(Int(0)),
            If(a > Int(0), i.store(i.load() + Int(1))),
            If(b > Int(0), i.store(i.load() + Int(1))),
            If(c > Int(0), i.store(i.load() + Int(1))),
            If(d > Int(0), i.store(i.load() + Int(1))),
            If(e > Int(0), i.store(i.load() + Int(1))),
        ]
    )

    y = Seq(
        [
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
        ]
    )

    return Seq([sort_1, sort_2, sort_3, sort_4, x, y])


def get_values():
    feed_1_value = App.globalGetEx(Int(1), price)
    feed_2_value = App.globalGetEx(Int(2), price)
    feed_3_value = App.globalGetEx(Int(3), price)
    feed_4_value = App.globalGetEx(Int(4), price)
    feed_5_value = App.globalGetEx(Int(5), price)

    var1 = ScratchVar(TealType.uint64)
    var2 = ScratchVar(TealType.uint64)
    var3 = ScratchVar(TealType.uint64)
    var4 = ScratchVar(TealType.uint64)
    var5 = ScratchVar(TealType.uint64)

    # TODO: for each feed_value slice the values and get last value
    # TODO: for each feed_timestamp slice the times and get last timestamp
    # TODO: check current timestamp and compare with feed timestamp
    validate_prices = Seq(
        [
            If(And(feed_1_value.hasValue(), (median_timestamp - Global.latest_timestamp()) > time_interval)).Then(
                var1.store(feed_1_value.value())
            )
            # Substring(feed_1_value.value(), Int(0), Int)
            .Else(var1.store(Int(0))),
            If(And(feed_2_value.hasValue(), time_interval < median_timestamp))
            .Then(var2.store(feed_2_value.value()))
            .Else(var2.store(Int(0))),
            If(And(feed_3_value.hasValue(), time_interval < median_timestamp))
            .Then(var3.store(feed_3_value.value()))
            .Else(var3.store(Int(0))),
            If(And(feed_4_value.hasValue(), time_interval < median_timestamp))
            .Then(var4.store(feed_4_value.value()))
            .Else(var4.store(Int(0))),
            If(And(feed_5_value.hasValue(), time_interval < median_timestamp))
            .Then(var5.store(feed_5_value.value()))
            .Else(var5.store(Int(0))),
        ]
    )

    return Seq(
        [
            App.globalPut(median_price, Medianizer(var1, var2, var3, var4, var5)),
            # TODO: slice timestamp or nah
            # TODO: slice feed value for timestamp
            If(App.globalGet(median_price) == var1.load(), App.globalPut(median_timestamp, feed_1_value)),
            Approve(),
        ]
    )
