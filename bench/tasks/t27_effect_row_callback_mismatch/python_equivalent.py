def fetch_billing_score(user_id):
    return user_id + 100


def main():
    values = [fetch_billing_score(x) for x in [1]]
    print(values[0])


if __name__ == "__main__":
    main()
