def update_with_clamp(xs, index, value):
    out = list(xs)
    if index < 0:
        index = 0
    if index >= len(out):
        index = len(out) - 1
    out[index] = value
    return out


def main():
    updated = update_with_clamp([10, 20, 30], 9, 99)
    print(updated[2])


if __name__ == "__main__":
    main()
