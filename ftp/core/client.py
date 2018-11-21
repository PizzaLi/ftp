# -*- coding: utf-8 -*-
import os
import socket
import sys
from getpass import getpass
from ftp.lib.logger import logger

logger = logger.get_logger('ftp.core.client')


class FtpClient(object):
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM

    def __init__(self, server_address):
        self.client_socket = socket.socket(self.address_family, self.socket_type)
        self.client_socket.connect(server_address)
        self.local_path = None
        self.chunk_size = 1024
        if self.authenticate():
            self.choose_command()

    def authenticate(self):
        """
        Execute the user authenticate, send a authenticate to the server;

        If client type a 'enter' directly, nothing will send to the server,
        if client type sys.exit(0) or close the socket, then a 'None' will send to server,
        Also, if server close the socket or type a sys.exit(0), then a None will send to client.
        """
        while True:
            user_info = ['authenticate']
            username = input('请输入用户名[q: 退出]: ')
            if username.lower() == 'q':
                sys.exit(0)
            elif username:
                user_info.append(username)
                while True:
                    password = getpass('请输入密码[q: 退出]: ')
                    if password.lower() == 'q':
                        sys.exit(0)
                    elif password:
                        user_info.append(password)
                        user_info = ' '.join(user_info)
                        status_code = self.send_command(user_info)[1]
                        if status_code == '200':
                            return True
                        else:
                            break
                    else:
                        continue
            else:
                continue

    def parse_command(self, command):
        """
        Parse command, if command is compliance, return True,
        else print the error message, nothing returned
        return: command
        return type: str
        """
        if command.strip().count(' ') == 2:
            command = command.strip().replace('~', os.environ['HOME'])
            self.local_path = command.split(' ')[1] if command[:3] == 'put' else command.split(' ')[2]
            if self.check_path(command):
                return command
            else:
                print('\033[1;31m源文件不存在，请重新输入\033[0m')
        else:
            print('\033[1;31m%s <源文件> <目标文件>\033[0m' % command[:3])

    def check_path(self, command):
        """
        Check if the source director is exists
        """
        if command[:3] == 'put':
            if os.path.exists(self.local_path) and not os.path.isdir(self.local_path):
                return True
        else:
            if os.path.exists(self.local_path):
                if os.path.isdir(self.local_path):
                    self.dest_path = os.path.join(self.local_path, command[1].split(os.path.sep)[-1])
                else:
                    verify_choose = input('\033[1;32m文件已存在，[覆盖/续传/取消(y/n/c)]\033[0m')
                    if verify_choose == 'y':
                        self.open_mode = 'wb'
                    elif verify_choose == 'n':
                        self.open_mode = 'ab'
                    else:
                        self.open_mode = None
                    self.dest_path = self.local_path
                return True
            else:
                if self.local_path.endswith(os.path.sep):
                    return
                else:
                    par_dir = self.local_path.split(os.path.sep)[:-1]
                    parent_path = os.path.sep.join(par_dir)
                    if not os.path.exists(parent_path):
                        return
                    else:
                        self.open_mode = 'wb'
                        self.dest_path = self.local_path
                        return True

    def send_command(self, data):
        """
        Send command to server, then print the response on the screen
        """
        self.client_socket.send(data.encode('utf-8'))
        response = self.client_socket.recv(self.chunk_size)
        print('\033[1;32m%s\033[0m' % response.decode('utf-8'))
        # Not all request need a response return, if needed,
        # return type is a list and the item is the values in server's operation_code
        return response.decode('utf-8').strip().split()

    def choose_command(self):
        """
        Given a loop receive the command from user, then pass it to send_command
        """
        while True:
            command = input('请输入命令[q: 退出]: ')
            if command.lower() == 'q':
                sys.exit(0)
            elif command.strip()[:3].lower() in ('put', 'get'):
                # command_type is 'put' or 'get'
                command_type = command.strip()[:3].lower()
                command = self.parse_command(command)
                if command:
                    command = 'command ' + command
                    file_status = self.send_command(command)
                    if command_type == 'put':
                        if file_status[1] == '206':continue
                        else:
                            verify_choose = input(file_status[2])
                            if verify_choose == 'y':
                                self.put()
                            else:continue
                    elif command_type == 'get':
                        if file_status[1] == '205':
                            verify_choose = input(file_status[2])
                            if verify_choose == 'y':
                                self.get()
                            else:
                                continue
                        else:
                            continue
                else:
                    continue
            elif command:
                command = 'command ' + command
                self.send_command(command)
            else:
                continue

    def put(self):
        """
        Given a loop to send file content
        """
        # Only string has encode method
        file_size = 'upload ' + str(os.path.getsize(self.local_path))
        self.client_socket.sendall(file_size.encode('utf-8'))
        establish_channel = self.client_socket.recv(self.chunk_size).decode('utf-8')
        print('\033[1;32m%s\033[0m' % establish_channel)
        if establish_channel.split(' ')[1] == '207':
            source_file = open(self.local_path, 'rb')
            # Every send 'chunk_size' bytes
            while True:
                data_bytes = source_file.read(self.chunk_size)
                if data_bytes:
                    self.client_socket.send(data_bytes)
                else:
                    print('\033[1;32mDone\033[0m')
                    break
        else:
            return

    def get(self):
        """
        Given a loop to write the file content received from server.
        """
        if not self.open_mode:
            return
        data_recv = ''.encode('utf-8')
        start_flag = None
        file_size = 0
        dest_file = None

        if self.open_mode == 'wb':
            dest_file = open(self.dest_path, self.open_mode)
            start_flag = 'download'
            self.client_socket.sendall(start_flag.encode('utf-8'))
            file_size = self.client_socket.recv(self.chunk_size)
        elif self.open_mode == 'ab':
            dest_file = open(self.dest_path, self.open_mode)
            file_size = os.path.getsize(self.dest_path)
            start_flag = 'recover ' + str(file_size)
            self.client_socket.sendall(start_flag.encode('utf-8'))
            file_size = self.client_socket.recv(self.chunk_size)
        while True:
            if len(data_recv) < int(file_size):
                data_bytes = self.client_socket.recv(self.chunk_size)
                data_recv += data_bytes
                dest_file.write(data_bytes)
            else:
                print('\033[1;32mDone!\033[0m')
                break


if __name__ == "__main__":
    # Get the arguments
    args = docopt(__doc__)
    host = args.get('<host>')
    port = int(args.get('<port>'))
    server_address = host, port
    # Create a ftpclient instance.
    ftpclient = FtpClient(server_address)
