from Queue import Empty
from collections import defaultdict
from multiprocessing import Process
from multiprocessing import Queue
import argparse
import mechanize
import os
import progressbar
import random
import xlrd


def vote(credentials_q, results_q, url):
    while True:
        try:
            username, password = credentials_q.get(block=True, timeout=5)
            b = mechanize.Browser()
            b.open(url)

            b.select_form(nr=0)
            b.form['username'] = username
            b.form['password'] = password
            r = b.submit()

            is_voting_link = lambda url: 'data-candidate-number' in dict(url.attrs)

            if r.geturl().endswith('/valitse'):
                candidate = random.choice(list(b.links(predicate=is_voting_link)))
                candidate_number = dict(candidate.attrs)['data-candidate-number']

                r = b.follow_link(candidate)
                b.select_form(nr=0)
                b.form['vote'] = candidate_number
                r = b.submit()

                if r.geturl().endswith('/kiitos'):
                    results_q.put(('success', username, int(candidate_number)))
                else:
                    results_q.put(('error', username, int(candidate_number)))
            elif r.geturl().endswith('/kiitos'):
                results_q.put(('already_voted', username, None))
            else:
                results_q.put(('error', username, None))
        except Empty:
            # We are done, let the process finish
            pass
        except Exception, msg:
            results_q.put(('fatal', username, str(msg)))


def main():
    parser = argparse.ArgumentParser(description='Creates random votes on a live system.')
    parser.add_argument('-p', '--processes', help='Number of processes to fork.', default=2, type=int)
    parser.add_argument('-u', '--url', help='The URL of the login page for the election site.')
    parser.add_argument('-v', '--voters', help='The Excel file containing the voter information.')
    args = parser.parse_args()

    creds = Queue()
    results = Queue()

    # Load the list of voters from the Excel file.
    sheet = xlrd.open_workbook(filename=os.path.abspath(os.path.join(os.getcwd(), args.voters))).sheet_by_index(0)
    num_voters = sheet.nrows - 1

    print "Read", num_voters, "voters from input file."

    # Initialize the queue with the voters in random order. This will allow
    # multiple scripts to run simultaneously with higher probability of success
    # for each.
    pairs = [(sheet.cell_value(row, 0), sheet.cell_value(row, 1)) for row in xrange(1, sheet.nrows)]
    random.shuffle(pairs)
    for pair in pairs:
        creds.put(pair)

    print "Created a randomized task queue"

    # Launch the processes to perform the voting
    procs = []
    for i in xrange(args.processes):
        p = Process(target=vote, args=(creds, results, args.url))
        p.start()
        procs.append(p)

    print "Forked", args.processes, "processes to handle the queue."
    print "Waiting for processes to finish."

    pbar = progressbar.ProgressBar(
        widgets=[progressbar.Percentage(), progressbar.Bar()],
        maxval=num_voters).start()
    stats = defaultdict(int)

    for i in xrange(num_voters):
        res, username, candidate = results.get(block=True)
        stats[res] += 1
        pbar.update(i + 1)
    pbar.finish()

    print "Cleaning up worker processes"
    for p in procs:
        p.join()

    print stats
