# -*- coding: utf-8 -*-
import os
import socket
import subprocess
from functools import partial

from ftp.model.config import ftpserverconfig
from ftp.lib.logger import logger

logger = logger.get_logger('ftp.core.server')

SERVER_ADDRESS = HOST, PORT = ftpserverconfig.server_address

operation_code = {
        '200': 'FTP/1.0 200 OK 登录成功',
        '201': 'FTP/1.0 201 登录失败',
        '203': 'FTP/1.0 203 不支持的命令',
        '204': 'FTP/1.0 204 文件已存在，是否覆盖？（y/n）',
        '205': 'FTP/1.0 205 请确认（y/n）',
        '206': 'FTP/1.0 206 不存在的目录',
        '207': 'FTP/1.0 207 开始上传',
        '208': 'FTP/1.0 208 不支持的文件类型',
        '209': 'FTP/1.0 209 不存在的文件',
    }


def _get_bytes_message(message):
    """
    return a dict, the value is bytes, cause we should send bytes on socket
    """
    return {k: bytes(v, 'utf-8') for k, v in message.items()}

_get_bytes = partial(_get_bytes_message, operation_code)


class FtpServer(object):
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 5

    def __init__(self):
        self.server_socket = server_socket = socket.socket(self.address_family, self.socket_type)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(SERVER_ADDRESS)
        server_socket.listen(self.request_queue_size)
        self.host, self.port = server_socket.getsockname()
        self.login_status = False
        self.dest_path = None
        self.file_status_put = False
        self.file_status_get = False
        self.message = _get_bytes()
        self.chunk_size = 1024

    def serve_forever(self):
        logger.debug('Serving on host: %s, port: %d' % (self.host, int(self.port)))
        server_socket = self.server_socket
        while True:
            logger.debug('Accepting connection from client...')
            self.client_socket, self.client_address = server_socket.accept()
            self.handle_request()

    def handle_request(self):
        """
        If client request is finished, then we should clean the data which generate from that
        client, recover everything to the request begin.
        i.e self.login_status = False, self.dest_path = None
        """
        while True:
            logger.debug('Receiving data from client %s:%s' % self.client_address)
            client_data_bytes = self.client_socket.recv(self.chunk_size)
            client_data_str = client_data_bytes.decode('utf-8') 
            print('\033[1;32mReceived data: %s\033[0m' % client_data_str)
            if client_data_str:
                self.parse_client_data(client_data_str)
            else:
                self.tear_down()
                break

    def parse_client_data(self, client_data):
        message = self.message
        client_data_list = client_data.split(' ')
        command_type = client_data_list[0]
        if command_type == 'authenticate':
            self.username = client_data_list[1]
            self.password = client_data_list[2]
            auth_status = self.authenticate()
            if self.login_status:
                self.client_socket.send(message['200'])
            else:
                self.client_socket.send(message['201'])
        elif command_type == 'command':
            self.file_status_put = False
            self.file_status_get = False
            self.dest_path = None
            try:
                command = getattr(self, client_data_list[1])
                command_list = self.parse_command(client_data_list[1:])
                command(command_list)
            except AttributeError:
                self.client_socket.send(message['203'])
        elif command_type == 'upload':
            self.put(client_data_list)
        elif command_type in ('download', 'recover'):
            self.get(client_data_list)

    def authenticate(self):
        user_info = dict()
        file_obj = open(ftpserverconfig.user_file)
        for line in file_obj:
            line_list = line.strip().split(',')
            user_info[line_list[0]] = line_list[1]
        if self.username in user_info and self.password == user_info[self.username]:
            self.login_status = True

    def parse_command(self, client_data_list):
        """
        parse the data from client, return a command list
        """
        command_list = list()
        if len(client_data_list) == 1 and client_data_list[0] == 'cd':
            client_data_list.append('~')
        for arg in client_data_list:
            if '~' in arg:
                arg = arg.replace('~', os.environ['HOME'])
            command_list.append(arg)
        return command_list

    def get_file_status(self, command):
        message = self.message
        command_type = command[0]
        dest_path = command[2] if command_type == 'put' else command[1]
        if command_type == 'put':
            if os.path.exists(dest_path):
                if os.path.isdir(dest_path):
                    # "command[1].split(os.path.sep)[-1]" is the source file name
                    # os.path.join() will ignore the slash at the end of the path.
                    self.dest_path = os.path.join(dest_path, command[1].split(os.path.sep)[-1])
                    self.client_socket.send(message['205'])
                else:
                    self.dest_path = dest_path
                    self.client_socket.send(message['204'])
            else:
                if dest_path.endswith(os.path.sep):
                    self.client_socket.send(message['206'])
                else:
                    self.dest_path = dest_path
                    self.client_socket.send(message['205'])
            self.file_status_put = True
        else:
            if os.path.exists(dest_path):
                if os.path.isdir(dest_path):
                    self.client_socket.send(message['208'])
                else:
                    self.dest_path = dest_path
                    self.client_socket.send(message['205'])
            else:
                self.client_socket.send(message['209'])
            self.file_status_get = True

    def ls(self, command):
        """
        If the argument shell=True is applied, child process will get all the environment
        variables, else not.
        """
        res = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # communicate() accepted an argument, if this argument is applied, then it will be passed to
        # stdin=subprocess.PIPE
        result = res.communicate()
        # Get the stdout message
        stdout = result[0]
        # Get the error message
        stderr = result[1]
        # communicate() returns bytes
        messages = stderr if stderr else stdout
        self.client_socket.send(messages)

    def cd(self, command=None):
        """
        If successed, no stdout and no errors
        If failed, only stderrs
        """
        last_dir = []
        res = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = res.communicate()
        stderr = result[1]
        messages = stderr if stderr else command[1].encode('utf-8')
        self.client_socket.send(messages)

    def put(self, command=None):
        """
        First, judge weather the file path status has been processed.
        If the value of status is True, Given a loop to receive file content from client
        """
        message = self.message
        if not self.file_status_put:
            self.get_file_status(command)
        else:
            file_size = int(command[1])
            data_recv = ''.encode('utf-8')
            try:
                dest_path = open(self.dest_path, 'wb')
                self.client_socket.send(message['207'])
            except FileNotFoundError:
                self.client_socket.send(message['206'])
                return
            while True:
                if len(data_recv) < file_size:
                    data = self.client_socket.recv(self.chunk_size)
                    data_recv += data
                    dest_path.write(data)
                else:
                    print('\033[1;32mDone!\033[0m')
                    self.dest_path = None
                    self.file_status_put = None
                    break

    def get(self, command=None):
        """
        Get file content, send to client
        """
        if not self.file_status_get:
            self.get_file_status(command)
        else:
            dest_file = open(self.dest_path, 'rb')
            if command[0] == 'download':
                file_size = os.path.getsize(self.dest_path)
                self.client_socket.send(str(file_size).encode('utf-8'))
            else:
                else_size = os.path.getsize(self.dest_path) - int(command[1])
                self.client_socket.send(str(else_size).encode('utf-8'))
                dest_file.seek(int(command[1]))
            while True:
                data_bytes = dest_file.read(self.chunk_size)
                if data_bytes:
                    self.client_socket.send(data_bytes)
                else:
                    print('\033[1;32mDone!\033[0m')
                    self.dest_path = None
                    self.file_status_get = None
                    break

    def tear_down(self):
        """
        Clear all temporary status
        """
        self.login_status = False
        self.finish_request()
        self.dest_path = None
        self.file_status_put = False
        self.file_status_get = False

    def finish_request(self):
        """
        Close client socket
        """
        self.client_socket.close()


if __name__ == "__main__":
    server = FtpServer()
    server.serve_forever()
