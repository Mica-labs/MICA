def check_restaurant_available(**kwargs):
    from mica.event import BotUtter, SetSlot
    return [BotUtter(f"The restaurant is available")]


def check_transfer_funds(**kwargs):
    from mica.event import BotUtter, SetSlot
    money = kwargs.get("amount_of_money")
    import random
    funds = random.randint(0, 20000)
    if money <= funds:
        return "has sufficient funds."
    return [BotUtter(f"funds: {funds}, insufficient funds.")]

def point_to_func(func_name, **kwargs):
    func = {"check_restaurant_available": check_restaurant_available, "check_transfer_funds": check_transfer_funds}
    return func.get(func_name)(**kwargs)
