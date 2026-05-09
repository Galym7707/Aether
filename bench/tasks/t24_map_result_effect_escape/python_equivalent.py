def audit_int(x):
    print(f"audit:{x}")
    return x


def main():
    result = ("Ok", 2)
    if result[0] == "Ok":
        audit_int(result[1])


if __name__ == "__main__":
    main()
