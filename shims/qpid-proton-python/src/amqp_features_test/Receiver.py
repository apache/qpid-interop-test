#!/usr/bin/env python

"""
AMQP features test receiver shim for qpid-interop-test
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

from json import dumps
import os.path
import sys
from traceback import format_exc

from proton.handlers import MessagingHandler
from proton.reactor import Container

class AmqpFeaturesTestReceiver(MessagingHandler):
    """
    Reciver shim for AMQP dtx test
    ...
    """
    def __init__(self, broker_url, queue_name, test_type, num_expected_messages_str):
        super(AmqpFeaturesTestReceiver, self).__init__()
        self.broker_url = broker_url
        self.queue_name = queue_name
        self.test_type = test_type
        self.received_value_list = []
        self.expected = int(num_expected_messages_str)
        self.received = 0
        self.remote_properties = None

    def get_received_value_list(self):
        """Return the received list of AMQP values"""
        return self.received_value_list

    def get_remote_properties(self):
        """Return the remote (broker) properties"""
        return self.remote_properties

    def on_start(self, event):
        """Event callback for when the client starts"""
        event.container.create_receiver('%s/%s' % (self.broker_url, self.queue_name))

    def on_connection_remote_open(self, event):
        """Callback for remote connection open"""
        self.remote_properties = event.connection.remote_properties
        if self.test_type == 'connection_property':
            event.connection.close()

    def on_message(self, event):
        """Event callback when a message is received by the client"""
        if event.message.id and event.message.id < self.received:
            return # ignore duplicate message
        if self.expected == 0 or self.received < self.expected:
            # do something here
            if self.received == self.expected:
                event.receiver.close()
                event.connection.close()

# --- main ---
# Args: 1: Broker address (ip-addr:port)
#       2: Queue name
#       3: Test type
#       4: Number of expected messages
try:
    RECEIVER = AmqpFeaturesTestReceiver(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    Container(RECEIVER).run()
    print sys.argv[3]
    if (sys.argv[3] == 'connection_property'):
        print dumps(RECEIVER.get_remote_properties())
    else:
        print dumps(RECEIVER.get_received_value_list())
 
except KeyboardInterrupt:
    pass
except Exception as exc:
    print os.path.basename(sys.argv[0]), 'EXCEPTION', exc
    print format_exc()
