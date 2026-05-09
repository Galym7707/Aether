def audit_error(message):
    print(f"audit:{message}")
    return message


def main():
    result = ("Err", "bad")
    if result[0] == "Err":
        audit_error(result[1])


if __name__ == "__main__":
    main()
