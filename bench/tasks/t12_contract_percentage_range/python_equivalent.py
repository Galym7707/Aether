def discounted_price(price, percent):
    return price - (price * percent // 100)


print(discounted_price(200, 150))
