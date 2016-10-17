#!/usr/bin/env python

"""
AMQP distributed transactions (DTX) test receiver shim for qpid-interop-test
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

import os.path
import sys
from traceback import format_exc

from proton.handlers import MessagingHandler
from proton.reactor import Container

class AmqpDtxTestReceiver(MessagingHandler):
    """
    Receiver shim for AMQP dtx test
    ...
    """
    def __init__(self, broker_url, queue_name):
        super(AmqpDtxTestReceiver, self).__init__()
        self.broker_url = broker_url
        self.queue_name = queue_name
        self.received_value_list = []
        self.expected = int('0')
        self.received = 0

    def get_received_value_list(self):
        """Return the received list of AMQP values"""
        return self.received_value_list

    def on_start(self, event):
        """Event callback for when the client starts"""
        event.container.create_receiver('%s/%s' % (self.broker_url, self.queue_name))

    def on_message(self, event):
        """Event callback when a message is received by the client"""
        if event.message.id and event.message.id < self.received:
            return # ignore duplicate message
        if self.expected == 0 or self.received < self.expected:
            # do something here
            if self.received >= self.expected:
                event.receiver.close()
                event.connection.close()

# --- main ---
# Args: 1: Broker address (ip-addr:port)
#       2: Queue name
#       ...
try:
    RECEIVER = AmqpDtxTestReceiver(sys.argv[1], sys.argv[2])
    Container(RECEIVER).run()
except KeyboardInterrupt:
    pass
except Exception as exc:
    print os.path.basename(sys.argv[0]), 'EXCEPTION', exc
    print format_exc()
