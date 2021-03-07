import time
import os
import sys
import hoverset.network.client as client
from hoverset.network.utils import prepare_header, json_decode, json_encode


class FileProperty:

    def __init__(self, path):
        self.mode, self.ino, self.dev, self.nlink, self.uid, self.gid, \
            self.size, self.accessed, self.modified, self.created = os.stat(path)
        self.path = path
        self.name = os.path.basename(self.path)


class BaseProtocol:

    def receive(self, data):
        # Receive transmitted data
        pass

    def read(self):
        # Provide data to be sent here. Data may be read repeatedly
        return b''

    def complete(self):
        # Terminate protocol here
        pass


class FileTransfer(BaseProtocol):
    handles = []
    name = "FileTransfer"
    location = "C:\\Users\\MANU\\Desktop"

    def __init__(self, json_header=None, file_path=None):
        self.json_header = json_header
        self.send_buffer = b''
        self.has_response = False
        self.file_path = file_path
        self.progress = 0
        self.file_properties = None
        self.progress_listener = None
        if file_path is not None:
            self.file_properties = FileProperty(file_path)
            self.descriptor = open(file_path, "rb", buffering=0)
            self.send_buffer += self.get_header()
            self.has_response = True
            self.file_size = self.file_properties.size
        else:
            self.file_size = json_header.get("file-size", 0)
            self.descriptor = open(os.path.join(self.location, json_header["file-name"]), "ab")
        self.transfer_time = None

    def receive(self, data):
        if self.transfer_time is None:
            self.transfer_time = time.time()
        self.descriptor.write(data)
        self.update_progress(len(data))

    def get_header(self):
        if self.file_path is None:
            return {}
        header = {
            "file-name": self.file_properties.name,
            "content-size": self.file_properties.size,
            "content-protocol": FileTransfer.name,
        }
        return prepare_header(header)

    def update_progress(self, value):
        self.progress += value
        if self.progress_listener:
            self.progress_listener(self.progress / self.file_size)

    def set_progress_listener(self, listener, *args, **kwargs):
        self.progress_listener = lambda progress: listener(progress, *args, **kwargs)

    def read(self):
        if self.transfer_time is None:
            self.transfer_time = time.time()
            data = self.send_buffer
            self.send_buffer = b''
            return data
        data = self.descriptor.read(4096)
        self.update_progress(len(data))
        return data

    @staticmethod
    def send(file_path, addr, progress_listener=None):
        handle = FileTransfer(None, file_path)
        handle.set_progress_listener(progress_listener)
        c = client.SimpleClient(*addr)
        c.connect(handle)
        c.start()
        return handle

    def complete(self):
        self.descriptor.close()
        # print("Transfer complete in {} s".format(time.time() - self.transfer_time))


class HostIdentity(BaseProtocol):
    name = "HostIdentity"

    def __init__(self, json_header=None):
        self.has_response = True
        self._recv_buff = b''
        self.on_complete_listener = None
        self.host_info = None
        if json_header is not None:
            # We have received another hosts info so we send our info as well.
            # Set the remote host info
            self._send_buff = json_encode(self.get_system_identity())
        else:
            # We are transmitting our information to get remote host info.
            self._send_buff = prepare_header(self.get_header()) + json_encode(self.get_system_identity())

    def read(self):
        # Send the host info that has been set on the buffer then empty buffer
        data = self._send_buff
        self._send_buff = b''
        return data

    def receive(self, data):
        self._recv_buff += data

    def get_header(self):
        return {"content-protocol": HostIdentity.name,
                "content-size": len(json_encode(self.get_system_identity()))}

    def complete(self):
        if self._recv_buff:
            self.host_info = json_decode(self._recv_buff)
            if self.on_complete_listener:
                self.on_complete_listener(self.host_info)

    def set_on_complete_listener(self, listener, *args, **kwargs):
        self.on_complete_listener = lambda info: listener(info, *args, **kwargs)

    def get_system_identity(self):
        env = os.environ
        platform = sys.platform
        info = {}
        if platform == 'win32':
            version = sys.getwindowsversion()
            info.update({
                "computer-name": env.get("COMPUTERNAME", "Unknown"),
                "user-name": env.get("USERNAME", "Unknown"),
                "windows-build": version[2],
                "windows-version": version[0],
                "os-platform": platform,
                "os-name": " ".join(("Windows", str(version[0])))
            })
        elif platform.startswith('linux'):
            info.update({
                "computer-name": env.get("NAME", "Unknown"),
                "user-name": env.get("USER", "Unknown"),
                "os-name": env.get("WSL_DISTRO_NAME", "Linux")
            })
        return info

    @staticmethod
    def request(addr, on_complete=None):
        handle = HostIdentity()
        handle.set_on_complete_listener(on_complete)
        c = client.ClientSystem()
        c.connect(*addr, handle)
        c.start()
        return handle


class SpeedTest(BaseProtocol):
    pass


if __name__ == '__main__':
    HostIdentity.request(('127.0.0.1', 65432), lambda x: print(x))
