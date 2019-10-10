"""
Jerome Paddick
"""
import csv
import re


class ProcessRow:

    def __init__(self, row):
        self.start_time = row["start_time"]
        self.end_time = row["end_time"]
        self.break_notes = row["break_notes"].replace(" ", "").lower()
        self.pay_rate = float(row["pay_rate"])

    def shift_start_end(self):
        """
        :return: start time and end time of shift, in decimal hours
        (number of hours since start of day eg. 17:30 ==> 17.5)
        """
        match_string = '^([0-1]\d|2[0-4])(:)([0-6]\d)'
        if re.fullmatch(match_string, self.start_time) and re.fullmatch(match_string, self.end_time):
            start_matches = re.match(match_string, self.start_time)
            start_time_decimal = int(start_matches.group(1)) + int(start_matches.group(3))/60
            end_matches = re.match(match_string, self.end_time)
            end_time_decimal = int(end_matches.group(1)) + int(end_matches.group(3))/60
            return start_time_decimal, end_time_decimal

    def break_start_end(self):
        """
        :return: start and end of break in decimal hours
        """
        match_string = '^(\d{1,2})[.:]?(\d{2})?(\D{2})?-(\d{1,2})[.:]?(\d{2})?(\D{2})?$'
        if re.fullmatch(match_string, self.break_notes):
            matches = re.match(match_string, self.break_notes)
            start_min = matches.group(2) if matches.group(2) else "00"
            end_min = matches.group(5) if matches.group(5) else "00"
            start_break_decimal = int(matches.group(1)) + int(start_min)/60
            end_break_decimal = int(matches.group(4)) + int(end_min)/60
            shift_start = self.shift_start_end()[0]

            if matches.group(3) == "pm" or (not matches.group(3) and matches.group(6) == "pm") or \
                    start_break_decimal < shift_start:
                start_break_decimal += 12
            if matches.group(6) == "pm" or end_break_decimal < shift_start:
                end_break_decimal += 12

            return start_break_decimal, end_break_decimal

    def worker_cost(self):
        """
        :return: total cost for worker over day
        """
        shift = self.shift_start_end()
        brk = self.break_start_end()
        day_cost = self.pay_rate*((shift[1] - shift[0]) - (brk[1] - brk[0]))
        return day_cost


def update_cost_dict(cost_dict, shift, pay_rate):
    if int(shift[0]) == int(shift[1]):
        cost_dict[str(int(shift[0])) + ":00"] += pay_rate*(shift[1] - shift[0])
    else:
        cost_dict[str(int(shift[0])) + ":00"] += pay_rate*(int(shift[0]+1) - shift[0])
        for x in range(int(shift[0]+1), int(shift[1]), 1):
            cost_dict[str(x) + ":00"] += pay_rate
        cost_dict[str(int(shift[1])) + ":00"] += (shift[1]) - int(shift[1])
    return cost_dict


def process_shifts(path_to_csv):
    """
    :param path_to_csv: The path to the work_shift.csv
    :type string:
    :return: A dictionary with time as key (string) with format %H:%M
        (e.g. "18:00") and cost as value (Number)
    For example, it should be something like :
    {
        "17:00": 50,
        "22:00: 40,
    }
    In other words, for the hour beginning at 17:00, labour cost was
    50 pounds
    :rtype dict:
    """

    cost_per_hour = {str(x)+":00": 0 for x in range(24)}

    with open(path_to_csv, "r") as csv_file:
        workers = [line for line in csv.DictReader(csv_file)]
    for worker in workers:
        row = ProcessRow(worker)
        s_start, s_end = row.shift_start_end()
        b_start, b_end = row.break_start_end()
        shift_1 = [s_start, b_start]
        shift_2 = [b_end, s_end]
        cost_per_hour = update_cost_dict(cost_per_hour, shift_1, row.pay_rate)
        cost_per_hour = update_cost_dict(cost_per_hour, shift_2, row.pay_rate)
    for x, y in cost_per_hour.items():
        if isinstance(y, float):
            cost_per_hour[x] = round(y, 2)
    return cost_per_hour


def process_sales(path_to_csv):
    """

    :param path_to_csv: The path to the transactions.csv
    :type string:
    :return: A dictionary with time (string) with format %H:%M as key and
    sales as value (string),
    and corresponding value with format %H:%M (e.g. "18:00"),
    and type float)
    For example, it should be something like :
    {
        "17:00": 250,
        "22:00": 0,
    },
    This means, for the hour beginning at 17:00, the sales were 250 dollars
    and for the hour beginning at 22:00, the sales were 0.

    :rtype dict:
    """
    sales_per_hour = {str(x)+":00": 0 for x in range(24)}
    with open(path_to_csv, "r") as csv_file:
        costs = [line for line in csv.DictReader(csv_file)]
    for row in costs:
        time = re.match("^(\d+):", row["time"])
        sales_per_hour[str(time.group(1)) + ":00"] += float(row["amount"])
    for x, y in sales_per_hour.items():
        if isinstance(y, float):
            sales_per_hour[x] = round(y, 2)
    return sales_per_hour



def compute_percentage(shifts, sales):
    """
    :param shifts:
    :type shifts: dict
    :param sales:
    :type sales: dict
    :return: A dictionary with time as key (string) with format %H:%M and
    percentage of labour cost per sales as value (float),
    If the sales are null, then return -cost instead of percentage
    For example, it should be something like :
    {
        "17:00": 20,
        "22:00": -40,
    }
    :rtype: dict
    """
    percentage_dict = {str(x)+":00": 0 for x in range(24)}
    for hour in percentage_dict.keys():
        if shifts[hour]:

            if sales[hour]:
                percentage_dict[hour] = round((shifts[hour]/sales[hour])*100, 2)
            else:
                percentage_dict[hour] = -shifts[hour]
    return percentage_dict

def best_and_worst_hour(percentages):
    """
    Args:
    percentages: output of compute_percentage
    Return: list of strings, the first element should be the best hour,
    the second (and last) element should be the worst hour. Hour are
    represented by string with format %H:%M
    e.g. ["18:00", "20:00"]
    """
    low_val = min([val for val in percentages.values()])
    low_hour = [key for key, val in percentages.items() if val == low_val]
    high_val = max([val for val in percentages.values()])
    high_hour = [key for key, val in percentages.items() if val == high_val]
    return low_hour[0], high_hour[0]

def main(path_to_shifts, path_to_sales):
    """
    Do not touch this function, but you can look at it, to have an idea of
    how your data should interact with each other
    """
    shifts_processed = process_shifts(path_to_shifts)
    sales_processed = process_sales(path_to_sales)
    percentages = compute_percentage(shifts_processed, sales_processed)
    best_hour, worst_hour = best_and_worst_hour(percentages)
    return best_hour, worst_hour

if __name__ == '__main__':
    # You can change this to test your code, it will not be used
    pass


"""
Jerome Paddick
"""
