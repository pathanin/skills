import csv


def read_addresses(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [row[0] for row in csv.reader(f) if row]
