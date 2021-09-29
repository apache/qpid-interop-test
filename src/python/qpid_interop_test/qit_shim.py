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

from qpid_interop_test.qit_errors import InteropTestTimeout


class ShimProcess(subprocess.Popen):
    """Abstract parent class for Sender and Receiver shim process"""
    def __init__(self, params, proc_name):
        self.proc_name = proc_name
        self.killed_flag = False
        self.env = copy.deepcopy(os.environ)
        super().__init__(params, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid, env=self.env)

    def wait_for_completion(self, timeout):
        """Wait for process to end and return tuple containing (stdout, stderr) from process"""
        timer = threading.Timer(timeout, self._kill, [timeout])
        try:
            timer.start()
            (stdoutdata, stderrdata) = self.communicate()
            stdoutstr =  stdoutdata.decode('ascii')
            stderrstr = stderrdata.decode('ascii')
            if self.killed_flag:
                raise InteropTestTimeout('%s: Timeout after %d seconds' % (self.proc_name, timeout))
            if self.returncode != 0:
                return 'Return code %d\nstderr=%s\nstdout=%s' % (self.returncode, stderrstr, stdoutstr)
            if stderrstr: # length > 0
                # Workaround for Amqp.NetLite which on some OSs produces a spurious error message on stderr
                # which should be ignored:
                # Workaround for deprecation warning on stderr:
                if not stderrstr.startswith('Got a bad hardware address length for an AF_PACKET') and \
                "[DEP0005]" not in stderrstr:
                    return 'stderr: %s\nstdout: %s' % (stderrstr, stdoutstr)
            if not stdoutstr: # zero length
                return None
            type_value_list = stdoutstr.split('\n')[0:-1] # remove trailing '\n', split by only remaining '\n'
            if len(type_value_list) == 2:
                try:
                    return (type_value_list[0], json.loads(type_value_list[1])) # Return tuple
                except ValueError:
                    return stdoutstr # ERROR: return single string
            return stdoutstr # ERROR: return single string
        except (KeyboardInterrupt) as err:
            self.send_signal(signal.SIGINT)
            raise err
        finally:
            timer.cancel()

    def _kill(self, timeout):
        """Method called when timer expires"""
        del timeout # unused
        self.kill()
        self.killed_flag = True


class Sender(ShimProcess):
    """Sender shim process"""
    def __init__(self, params, proc_name='Sender'):
        #print('\n>>>SNDR>>> %s' % params)
        super().__init__(params, proc_name)

class Receiver(ShimProcess):
    """Receiver shim process"""
    def __init__(self, params, proc_name='Receiver'):
        #print('\n>>>RCVR>>> %s' % params)
        super().__init__(params, proc_name)

class Shim:
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
        return Sender(args)

    def create_receiver(self, broker_addr, queue_name, test_key, json_test_str):
        """Create a new receiver instance"""
        args = []
        args.extend(self.receive_params)
        args.extend([broker_addr, queue_name, test_key, json_test_str])
        return Receiver(args)


class ProtonPython3Shim(Shim):
    """Shim for qpid-proton Python client"""
    NAME = 'ProtonPython3'
    def __init__(self, sender_shim, receiver_shim):
        super().__init__(sender_shim, receiver_shim)
        self.send_params = ['python3', self.sender_shim]
        self.receive_params = ['python3', self.receiver_shim]


class ProtonCppShim(Shim):
    """Shim for qpid-proton C++ client"""
    NAME = 'ProtonCpp'
    def __init__(self, sender_shim, receiver_shim):
        super().__init__(sender_shim, receiver_shim)
        self.send_params = [self.sender_shim]
        self.receive_params = [self.receiver_shim]


class RheaJsShim(Shim):
    """Shim for Rhea Javascript client"""
    NAME = 'RheaJs'
    def __init__(self, sender_shim, receiver_shim):
        super().__init__(sender_shim, receiver_shim)
        self.send_params = [self.sender_shim]
        self.receive_params = [self.receiver_shim]


class QpidJmsShim(Shim):
    """Shim for qpid-jms JMS client"""
    NAME = 'QpidJms'
    JMS_CLIENT = True

    JAVA_HOME = os.getenv('JAVA_HOME', '/usr')
    JAVA_EXEC = os.path.join(JAVA_HOME, 'bin', 'java')

    def __init__(self, dependency_class_path, sender_shim, receiver_shim):
        super().__init__(sender_shim, receiver_shim)
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
        super().__init__(sender_shim, receiver_shim)
        self.send_params = ['dotnet', self.sender_shim]
        self.receive_params = ['dotnet', self.receiver_shim]
