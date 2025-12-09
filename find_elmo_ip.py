import socket
import netifaces
import threading


CONTEXT = {
    "scanning_robots": False,
    "robot_model": ""
}


def callback(robot_name, robot_address):
        """Callback function called when a robot is found"""
        print(f"Found robot: {robot_name} at {robot_address}")

def scan_robots(cb, models=[]):
    def scan_robots_runnable():
        previous = None
        while CONTEXT["scanning_robots"]:
            try:
                interfaces = netifaces.interfaces()
                allips = []
                for i in interfaces:
                    try:
                        allips.append(netifaces.ifaddresses(i)[netifaces.AF_INET][0]["addr"])
                    except:
                        pass
                msg = b'ruarobot'
                for ip in allips:
                    if "127.0.0" in ip:
                        continue
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)  # UDP
                    sock.settimeout(1)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.bind((ip,0))
                    sock.sendto(msg, ("255.255.255.255", 5000))
                    try:
                        while True:
                            data, address = sock.recvfrom(1024)
                            #print(data)
                            if previous == address[0]:
                                    CONTEXT["scanning_robots"] = False
                                    return
                            if b"iamarobot" in data:
                                _, robot_model, robot_name, server_port = data.decode("utf-8").split(";")
                                if CONTEXT["robot_model"]:
                                    if robot_model == CONTEXT["robot_model"]:
                                        cb(robot_name, "http://%s:%s" % (address[0], server_port))
                                else:
                                    cb(robot_name, "http://%s:%s" % (address[0], server_port))
                                
                                previous = address[0]
                    except socket.timeout:
                        sock.close()
            except:
                pass
    CONTEXT["scanning_robots"] = True
    t = threading.Thread(target=scan_robots_runnable)
    t.start()


scan_robots(callback)