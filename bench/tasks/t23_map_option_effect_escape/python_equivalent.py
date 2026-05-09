def audit_int(x):
    print(f"audit:{x}")
    return x


def main():
    [audit_int(x) for x in [1]]


if __name__ == "__main__":
    main()
