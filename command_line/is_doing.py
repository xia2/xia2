def tail(filename):
    for record in open(filename):
        print(record[:-1])
    return


def main():
    filename = None
    for record in open("xia2-debug.txt"):
        if record.startswith("Logfile:"):
            filename = record.split("->")[-1].strip()
    if filename:
        tail(filename)


if __name__ == "__main__":
    main()
