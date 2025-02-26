from schwebsearch import fetch_sch_database


def main():
    data = fetch_sch_database()
    for i, col in enumerate(data.columns):
        print(i, col)
    print(data.shape)
    print("Fim")


if __name__ == "__main__":
    main()
