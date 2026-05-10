def identity(x):
    return x


def singleton(x):
    return [x]


def main():
    xs = singleton(5)
    ys = identity([1, 2])
    opt = 7
    res = 9
    print(xs[0])
    print(ys[1])
    print(opt)
    print(res)


if __name__ == "__main__":
    main()
