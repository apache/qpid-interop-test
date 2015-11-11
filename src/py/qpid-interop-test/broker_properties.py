"""
Module containing a small client which connects to the broker and
gets the broker connection properties so as to identify the broker.
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

from proton.handlers import MessagingHandler
from proton.reactor import Container

class BrokerClient(MessagingHandler):
    """
    Client to connect to broker and collect connection properties, used to identify the test broker
    """
    def __init__(self, url):
        super(BrokerClient, self).__init__()
        self.url = url
        self.remote_properties = None

    def on_start(self, event):
        """Event loop start"""
        event.container.create_sender(self.url)

    def on_sendable(self, event):
        """Sender link has credit, can send messages. Get connection properties, then close connection"""
        self.remote_properties = event.sender.connection.remote_properties
        event.sender.connection.close()

    def get_connection_properties(self):
        """Return the connection properties"""
        return self.remote_properties


def getBrokerProperties(broker_url):
    """Start client, then return its connection properties"""
    MSG_HANDLER = BrokerClient(broker_url)
    Container(MSG_HANDLER).run()
    return MSG_HANDLER.get_connection_properties()
