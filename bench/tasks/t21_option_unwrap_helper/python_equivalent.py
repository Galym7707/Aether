def get_or_zero(xs, index):
    try:
        return xs[index]
    except IndexError:
        return 0


def main():
    print(get_or_zero([10, 20], 9))


if __name__ == "__main__":
    main()
