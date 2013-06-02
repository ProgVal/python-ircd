import unittest
import socket
import time

from config import config


class Client(object):
    test_case = None

    def __init__(self, name):
        self.name = name
        self.socket = socket.socket()
        self.socket.connect((config.get('server', 'listen_host'), config.getint('server', 'listen_port')))
        self.socket.setblocking(0)
        self.socket_file = self.socket.makefile()
        self.responses = []

    def write(self, msg):
        self.responses.append([])
        print '<- [%s] %s' % (self.name, msg)
        self.socket_file.write(msg + '\r\n')
        self.socket_file.flush()

    def expect(self, line):
        got = None
        while got != line:
            try:
                got = self.socket_file.readline().strip()
            except socket.error:
                time.sleep(1)
                try:
                    got = self.socket_file.readline().strip()
                except socket.error, e:
                    self.test_case.fail('Socket error, probably didn\'t get response in time. Was waiting for line:\n' +
                                        line + '\n' +
                                        'Error: %s' % e)
            print '-> [%s] %s' % (self.name, got)
            self.responses[-1].append(got)

    def __str__(self):
        return self.name


class HappyTests(unittest.TestCase):
    n = 0

    @classmethod
    def setUpClass(cls):
        Client.test_case = None

    @classmethod
    def _increment_n(cls):
        cls.n += 1

    def setUp(self):
        self._increment_n()
        self.c1 = Client('alice-%s' % self.n)
        self.c2 = Client('bob-%s' % self.n)
        self.c3 = Client('charlie-%s' % self.n)
        Client.test_case = self

    def test_login_nick_first(self, c=None):
        if c is None: c = self.c1
        c.write('NICK %s' % c.name)
        c.write('USER %s %s %s %s' % (c.name, c.name, socket.getfqdn(), c.name))
        c.expect(':localhost 376 %s :End of MOTD command' % c.name)

    def test_login_user_first(self, c=None):
        if c is None: c = self.c2
        c.write('USER %s %s %s %s' % (c.name, c.name, socket.getfqdn(), c.name))
        c.write('NICK %s' % c.name)
        c.expect(':localhost 376 %s :End of MOTD command' % c.name)

    def test_join(self, c=None, channel=None, users=None):
        if c is None: c = self.c1
        if channel is None: channel = '#ch-%s' % self.n
        if users is None: users = []
        users.append(c)
        expected_username_list = ' '.join([c.name for c in users])
        if len(users) > 1:
            expected_username_list = ':' + expected_username_list
        self.test_login_nick_first(c)
        c.write('JOIN %s' % channel)
        c.expect(':localhost 353 %s = %s %s' % (c.name, channel, expected_username_list))
        c.expect(':localhost 366 %s :End of NAMES list' % c.name)

    def test_user_list_after_join(self):
        self.test_join(self.c1)
        self.test_join(self.c2, users=[self.c1])

    def test_message_to_channel(self, c=None, rc=None, channel=None, msg='test message'):
        if c is None: c = self.c1
        if channel is None: channel = '#ch-%s' % self.n
        if rc is None:
            if c is self.c1: rc = self.c2
            else: rc = self.c1
        self.test_user_list_after_join()
        c.write('PRIVMSG %s :%s' % (channel, msg))
        rc.expect(':{c}!{c}@localhost. PRIVMSG {channel} :{msg}'.format(
            c=c, channel=channel, msg=msg))

