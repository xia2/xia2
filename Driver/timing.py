from __future__ import absolute_import, division, print_function

_timing_db = []


def record(timing_information):
    """
    Add a timing record to a global database.

    :param timing_information: a dictionary in the format
       {"command": "command line string",
        "time_start": unix epoch timestamp,
        "time_end": unix epoch timestamp}
    """
    _timing_db.append(timing_information)


def report():
    """
    Visualise all recorded program executions in a flow diagram

    :return: A list of strings
    """
    return visualise_db(_timing_db)


def reset():
    """
    Remove all records from the global database
    """
    global _timing_db
    _timing_db = []


def visualise_db(timing_db):
    """
    Visualises program execution in a flow diagram given a list of timestamps.

    :param timing_db: A list of dictionaries, each in the format of
       {"command": "command line string",
        "time_start": unix epoch timestamp,
        "time_end": unix epoch timestamp}
    :return: A list of strings
    """
    if not timing_db:
        return []

    # prepare a few helper data structures
    ordered_by_start = list(
        sorted((t["time_start"], n) for n, t in enumerate(timing_db))
    )
    start_order = tuple(n for _, n in ordered_by_start)
    ordered_by_end = list(sorted((t["time_end"], n) for n, t in enumerate(timing_db)))

    relative_start_time = ordered_by_start[0][0]
    total_runtime = ordered_by_end[-1][0] - relative_start_time
    index_width = len(str(len(timing_db)))
    time_width = len("%.1f" % total_runtime)
    output = []
    running_tasks = []

    # annotate the dictionaries with useful information
    for n, t in enumerate(timing_db):
        t["index"] = start_order.index(n) + 1
        t["runtime"] = t["time_end"] - t["time_start"]
        t["short_command"] = t["command"].split(" ")[0]

    while ordered_by_start:
        timestamp, n = ordered_by_start.pop(0)

        tree_view = [" " if task is None else u"\u2502" for task in running_tasks]

        if ordered_by_end[0][1] == n and (
            not ordered_by_start or ordered_by_start[0][0] >= ordered_by_end[0][0]
        ):
            tree_view.append(u"\u25EF")
            ordered_by_end.pop(0)
        else:
            tree_view.append(u"\u252C")
            running_tasks.append(n)
        t = timing_db[n]
        output.append(
            u"{timestamp:{time_width}.1f}s  {t[index]:>{index_width}}. {tree_view:<5} {t[short_command]} ({t[runtime]:.1f}s)".format(
                t=t,
                tree_view=" ".join(tree_view),
                index_width=index_width,
                time_width=time_width,
                timestamp=timestamp - relative_start_time,
            )
        )
        # to debug:
        # output[-1] += " {t[time_start]} {t[time_end]} ({n})".format(t=t, n=n)

        # check for any finishing tasks before the next one starts
        while running_tasks and (
            not ordered_by_start or ordered_by_end[0][0] < ordered_by_start[0][0]
        ):
            timestamp, finishing_task = ordered_by_end.pop(0)
            output_line = "{timestamp:{time_width}.1f}s  {nothing:{index_width}}  ".format(
                nothing="",
                index_width=index_width,
                time_width=time_width,
                timestamp=timestamp - relative_start_time,
            )
            for n, task in enumerate(running_tasks):
                if task is None:
                    output_line += "  "
                elif task == finishing_task:
                    output_line += u"\u2534 "
                    running_tasks[n] = None
                else:
                    output_line += u"\u2502 "
            output.append(output_line)
            while running_tasks and running_tasks[-1] is None:
                running_tasks.pop()

    output.append("")
    output.append("Longest times:")
    timing_by_time = sorted(timing_db, key=lambda x: x["runtime"], reverse=True)
    for t in timing_by_time[0:10]:
        output.append(
            "{t[runtime]:{time_width}.1f}s: {t[index]:>{index_width}}. {t[command]}".format(
                t=t, index_width=index_width, time_width=time_width
            )
        )
    return output
