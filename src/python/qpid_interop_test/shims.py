"""
Module containing worker thread classes and shims
"""
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import copy
import json
import os
import signal
import subprocess
import threading

from qpid_interop_test.interop_test_errors import InteropTestTimeout


class ShimProcess(subprocess.Popen):
    """Abstract parent class for Sender and Receiver shim process"""
    def __init__(self, args, python3_flag, proc_name):
        self.proc_name = proc_name
        self.killed_flag = False
        self.env = copy.deepcopy(os.environ)
        if python3_flag:
            self.env['PYTHONPATH'] = self.env['PYTHON3PATH']
        super(ShimProcess, self).__init__(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid,
                                          env=self.env)

    def wait_for_completion(self, timeout):
        """Wait for process to end and return tuple containing (stdout, stderr) from process"""
        timer = threading.Timer(timeout, self._kill, [timeout])
        try:
            timer.start()
            (stdoutdata, stderrdata) = self.communicate()
            if self.killed_flag:
                raise InteropTestTimeout('%s: Timeout after %d seconds' % (self.proc_name, timeout))
            if stderrdata: # length > 0
                return stderrdata # ERROR: return single string
            if not stdoutdata: # zero length
                return None
            type_value_list = stdoutdata.split('\n')[0:-1] # remove trailing '\n', split by only remaining '\n'
            if len(type_value_list) == 2:
                try:
                    return (type_value_list[0], json.loads(type_value_list[1])) # Return tuple
                except ValueError:
                    return stdoutdata # ERROR: return single string
            return stdoutdata # ERROR: return single string
        except (KeyboardInterrupt) as err:
            self.send_signal(signal.SIGINT)
            raise err
        finally:
            timer.cancel()

    def _kill(self, timeout):
        """Method called when timer expires"""
        self.kill()
        self.killed_flag = True


class Sender(ShimProcess):
    """Sender shim process"""
    def __init__(self, params, python3_flag, proc_name='Sender'):
        print('\n>>>SNDR>>> %s python3_flag=%s' % (params, python3_flag))
        super(Sender, self).__init__(params, python3_flag, proc_name)

class Receiver(ShimProcess):
    """Receiver shim process"""
    def __init__(self, params, python3_flag, proc_name='Receiver'):
        print('\n>>>RCVR>>> %s python3_flag=%s' % (params, python3_flag))
        super(Receiver, self).__init__(params, python3_flag, proc_name)

class Shim(object):
    """Abstract shim class, parent of all shims."""
    NAME = ''
    JMS_CLIENT = False # Enables certain JMS-specific message checks
    def __init__(self, sender_shim, receiver_shim):
        self.sender_shim = sender_shim
        self.receiver_shim = receiver_shim
        self.send_params = None
        self.receive_params = None
        self.use_shell_flag = False

    def create_sender(self, broker_addr, queue_name, test_key, json_test_str):
        """Create a new sender instance"""
        args = []
        args.extend(self.send_params)
        args.extend([broker_addr, queue_name, test_key, json_test_str])
        return Sender(args, 'Python3' in self.NAME)

    def create_receiver(self, broker_addr, queue_name, test_key, json_test_str):
        """Create a new receiver instance"""
        args = []
        args.extend(self.receive_params)
        args.extend([broker_addr, queue_name, test_key, json_test_str])
        return Receiver(args, 'Python3' in self.NAME)


class ProtonPython2Shim(Shim):
    """Shim for qpid-proton Python client"""
    NAME = 'ProtonPython2'
    def __init__(self, sender_shim, receiver_shim):
        super(ProtonPython2Shim, self).__init__(sender_shim, receiver_shim)
        self.send_params = ['python', self.sender_shim]
        self.receive_params = ['python', self.receiver_shim]


class ProtonPython3Shim(Shim):
    """Shim for qpid-proton Python client"""
    NAME = 'ProtonPython3'
    def __init__(self, sender_shim, receiver_shim):
        super(ProtonPython3Shim, self).__init__(sender_shim, receiver_shim)
        self.send_params = ['python3', self.sender_shim]
        self.receive_params = ['python3', self.receiver_shim]


class ProtonCppShim(Shim):
    """Shim for qpid-proton C++ client"""
    NAME = 'ProtonCpp'
    def __init__(self, sender_shim, receiver_shim):
        super(ProtonCppShim, self).__init__(sender_shim, receiver_shim)
        self.send_params = [self.sender_shim]
        self.receive_params = [self.receiver_shim]


class RheaJsShim(Shim):
    """Shim for Rhea Javascript client"""
    NAME = 'RheaJs'
    def __init__(self, sender_shim, receiver_shim):
        super(RheaJsShim, self).__init__(sender_shim, receiver_shim)
        self.send_params = [self.sender_shim]
        self.receive_params = [self.receiver_shim]


class QpidJmsShim(Shim):
    """Shim for qpid-jms JMS client"""
    NAME = 'QpidJms'
    JMS_CLIENT = True

    JAVA_HOME = os.getenv('JAVA_HOME', '/usr/bin') # Default only works in Linux
    JAVA_EXEC = os.path.join(JAVA_HOME, 'java')

    def __init__(self, dependency_class_path, sender_shim, receiver_shim):
        super(QpidJmsShim, self).__init__(sender_shim, receiver_shim)
        self.dependency_class_path = dependency_class_path
        self.send_params = [self.JAVA_EXEC, '-cp', self.get_java_class_path(), self.sender_shim]
        self.receive_params = [self.JAVA_EXEC, '-cp', self.get_java_class_path(), self.receiver_shim]

    def get_java_class_path(self):
        """Method to construct and return the Java class path necessary to run the shim"""
        return self.dependency_class_path

class AmqpNetLiteShim(Shim):
    """Shim for AMQP.Net Lite client"""
    NAME = 'AmqpNetLite'
    def __init__(self, sender_shim, receiver_shim):
        super(AmqpNetLiteShim, self).__init__(sender_shim, receiver_shim)
        self.send_params = ['mono', self.sender_shim]
        self.receive_params = ['mono', self.receiver_shim]
