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

class Client(MessagingHandler):
    """
    Client to connect to broker and collect connection properties, used to identify the test broker
    """
    def __init__(self, url):
        super(Client, self).__init__()
        self.url = url
        self.remote_properties = None

    def on_connection_remote_open(self, event):
        """Callback for remote connection open"""
        self.remote_properties = event.connection.remote_properties
        event.connection.close()

    def on_start(self, event):
        """Event loop start"""
        event.container.connect(url=self.url)

    def get_connection_properties(self):
        """Return the connection properties"""
        return self.remote_properties


def get_broker_properties(broker_url):
    """Start client, then return its connection properties"""
    msg_handler = Client(broker_url)
    Container(msg_handler).run()
    return msg_handler.get_connection_properties()
