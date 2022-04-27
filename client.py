#! /usr/bin/env python

import argparse
import zmq
from typing import List
from threading import Thread
import re


from server import START, STOP, RUN_BATCH
from server import to_bytes as b
from server import to_string as s


def receive_results(port, outfile):
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f'tcp://127.0.0.1:{port}')
    print("C.receive_results: starting")

    with open(outfile, 'w') as fh:
        while True:
            status, result = socket.recv_multipart()
            socket.send(b'Recevied')
            status = s(status)
            # print(status)
            if status == 'DONE':
                print('terminating receive results thread')
                return
            fh.write(result.decode('UTF-8'))
            fh.flush()


def run_query(ports, query: List, outpath: str, sample_id: str):
    """
    :param port:
    :param query:
        ['RUN_BATCH'], 'path/to/reads.fq']
        ['STOP',]
    :return:
    """
    context = zmq.Context()

    #  Socket to talk to server
    print("Connecting to service")
    socket = context.socket(zmq.REQ)

    # Start thread for receiving input
    recv_thread = Thread(target=receive_results, args=(ports[1], outpath))
    recv_thread.start()

    socket.connect(f"tcp://127.0.0.1:5555")

    reads_sent = 0

    if query[0] == STOP:
        socket.send_multipart([b(STOP), b(sample_id)])
        print("Sending request %s …" % query[0])
    else:
        with open(query[1], 'r') as fh:
            socket.send_multipart([b(START), b(sample_id)])
            socket.recv()
            while True:
                # There wsa a suggestion to send all the reads from a sample
                # as a single message. But this would require reading the whole
                # fastq file into memory first
                seq = fh.read(1000000)
                batch_size = len(re.findall('^@', seq, re.MULTILINE))
                reads_sent += batch_size

                if seq:
                    socket.send_multipart(
                        [b(RUN_BATCH), b(str(seq)), b('NOTDONE')])
                    # It is required to receive with the REQ/REP pattern, even
                    # if the msg is not used
                    socket.recv()
                else:
                    # The output from kraken is buffered at 458752
                    # (~ 1064-1084 lines of output)
                    # This bodge sends in 6000 seqs to ensure all the real
                    # outputs are flushed. More fake seqs are needed as the
                    # output of unclassified reads takes up less space.
                    # There's probably a better solution
                    # for f in range(10000):
                    #     socket.send_multipart([b(RUN_BATCH), b(fakeseq)])
                    #     socket.recv()
                    #     print(f)

                    # Instead of a NOTDONE message, send the total number of
                    # Sequences sent for this sample
                    socket.send_multipart(
                        [b(RUN_BATCH), b('?'), b('DONE')])
                    socket.recv()
                    print('elephant')
                    break
            print('toast done')
    # recv_thread.terminate()



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--ports", nargs='+')
    parser.add_argument("--query", nargs='+')
    parser.add_argument("--out")
    parser.add_argument("--sample_id")

    args = parser.parse_args()
    run_query(args.ports, args.query, args.out, args.sample_id)

