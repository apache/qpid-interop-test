#!/bin/bash

# JARS
MVN_LOCAL_REPOSITORY=${HOME}/.m2/repository
QPID_JMS_CLIENT_LOCATION=${MVN_LOCAL_REPOSITORY}/org/apache/qpid/qpid-jms-client

echo "Available qpid-jms client versions:"
for d in ${QPID_JMS_CLIENT_LOCATION}/*; do
    if [ -d ${d} ]; then
		echo "  ${d##*/}"
    fi
done

# TODO: get this from the above list, which needs sorting to find latest version by default
JMS_VERSION=0.8.0-SNAPSHOT
echo "Current qpid-jms client version: ${JMS_VERSION}"

JMS_API=${MVN_LOCAL_REPOSITORY}/org/apache/geronimo/specs/geronimo-jms_1.1_spec/1.1.1/geronimo-jms_1.1_spec-1.1.1.jar:${QPID_JMS_CLIENT_LOCATION}/${JMS_VERSION}/qpid-jms-client-${JMS_VERSION}.jar
JSON_API=../../jars/javax.json-api-1.0.jar
CLASSPATH=${JMS_API}:${JSON_API}

BASEPATH=org/apache/qpid/interop_test/shim
SRCPATH=src/main/java/${BASEPATH}
TARGETPATH=target

mkdir -p ${TARGETPATH}/classes
javac -cp ${CLASSPATH} -Xlint:unchecked -d ${TARGETPATH}/classes ${SRCPATH}/AmqpSender.java ${SRCPATH}/AmqpReceiver.java  ${SRCPATH}/JmsSenderShim.java ${SRCPATH}/JmsReceiverShim.java
jar -cf ${TARGETPATH}/qpid-jms-shim.jar -C ${TARGETPATH}/classes ${BASEPATH}/AmqpSender.class -C ${TARGETPATH}/classes ${BASEPATH}/AmqpSender\$1.class -C ${TARGETPATH}/classes ${BASEPATH}/AmqpSender\$MyExceptionListener.class -C ${TARGETPATH}/classes ${BASEPATH}/AmqpReceiver.class -C ${TARGETPATH}/classes ${BASEPATH}/AmqpReceiver\$1.class -C ${TARGETPATH}/classes ${BASEPATH}/AmqpReceiver\$MyExceptionListener.class  -C ${TARGETPATH}/classes ${BASEPATH}/JmsSenderShim.class -C ${TARGETPATH}/classes ${BASEPATH}/JmsSenderShim\$1.class -C ${TARGETPATH}/classes ${BASEPATH}/JmsSenderShim\$MyExceptionListener.class -C ${TARGETPATH}/classes ${BASEPATH}/JmsReceiverShim.class -C ${TARGETPATH}/classes ${BASEPATH}/JmsReceiverShim\$1.class -C ${TARGETPATH}/classes ${BASEPATH}/JmsReceiverShim\$MyExceptionListener.class
