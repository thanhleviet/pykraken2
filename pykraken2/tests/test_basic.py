"""pykraken tests."""

from pathlib import Path
import subprocess as sub
from threading import Thread
import unittest

from pykraken2.client import Client
from pykraken2.server import Server


class SimpleTest(unittest.TestCase):
    """Test class."""

    @classmethod
    def setUpClass(self):
        """Set paths and other variables for tests."""
        data_dir = Path(__file__).parent / 'test_data'
        self.outdir = data_dir / 'output'
        self.database = data_dir / 'db'
        self.fastq1 = data_dir / 'reads1.fq'
        self.fastq2 = data_dir / 'reads2.fq'
        self.correct1 = data_dir / 'correct_output' / 'k2out1.tsv'
        self.correct2 = data_dir / 'correct_output' / 'k2out2.tsv'
        self.ports = [5555, 5556]
        self.address = '127.0.0.1'
        self.threads = 4
        self.k2_binary = Path(
            __file__).parent.parent / 'bin' / 'kraken2_linux' / 'kraken2'

    # def tearDown(self) -> None:
    #     sub.call('kill -9 $(lsof -i tcp:5555-5556)', shell=True)
    @unittest.skip
    def test_001_check_kraken_binary(self):
        """Test the bundled kraken2 binary."""
        try:
            sub.check_output([self.k2_binary, '--help'])
        except sub.CalledProcessError as e:
            self.assertTrue(False)
            self.skipTest(f"Kraken binary not working\n {e}")
        else:
            self.assertTrue(True)

    def test_002_create_server(self):
        """Test the server API."""
        server = Server(
            self.address, self.ports, self.database,
            self.k2_binary, self.threads)
        server.run()
        server.terminate()

    # def test_002_create_client(self):
    #     client = Client()
    #
    # def test_010_process_fastq(self):
    #     server= Server()
    #     client = client()
    #
    #     server.start()
    #     results = list(client.process_fastq(self.fastq1))
    #     # TODO: check results
    #     assert False

    # @unittest.skip
    def test_020_multi_client(self):
        """Client/server integration testing.

        A server instance and two client instances are run on threads.
        The results yielded by client.process_fastq and saved to a list.
        These results are compared to expected kraken2 results generated
        from using kraken2 directly.
        """
        def client_runner(sample_id, input_, results):
            client = Client(self.address, self.ports, sample_id)
            for chunk in client.process_fastq(input_):
                results.extend(chunk)

        server = Server(
            self.address, self.ports, self.database,
            self.k2_binary, self.threads)
        server_thread = Thread(target=server.run)
        server_thread.start()

        # Data for 2 client instances
        # [Sample_id, input, expected output, empty results list]
        client_data = [
            ['1', self.fastq1, self.correct1, []],
            ['2', self.fastq2, self.correct2, []]
        ]

        for cdata in client_data:
            thread = Thread(
                target=client_runner, args=(cdata[0], cdata[1], cdata[3]))
            # Put thread object onto client_data
            cdata.append(thread)
            thread.start()

        for t in client_data:
            t[4].join()

        # Compare the outputs
        for t in client_data:
            with open(t[2], 'r') as corr_fh:
                corr_line = corr_fh.readlines()
                corr_str = ''.join(corr_line)

                clinet_str = ''.join(t[3])
                self.assertEqual(corr_str, clinet_str)

        server.terminate()
