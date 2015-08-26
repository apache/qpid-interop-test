#!/bin/bash

# JARS
JMS_API=${HOME}/.m2/repository/org/apache/geronimo/specs/geronimo-jms_1.1_spec/1.1.1/geronimo-jms_1.1_spec-1.1.1.jar:${HOME}/.m2/repository/org/apache/qpid/qpid-jms-client/0.4.0-SNAPSHOT/qpid-jms-client-0.4.0-SNAPSHOT.jar
JSON_API=../../jars/javax.json-api-1.0.jar
CLASSPATH=${JMS_API}:${JSON_API}

BASEPATH=org/apache/qpid/interop_test/shim
SRCPATH=src/main/java/${BASEPATH}
TARGETPATH=target

mkdir -p ${TARGETPATH}/classes
javac -cp ${CLASSPATH} -Xlint:unchecked -d ${TARGETPATH}/classes ${SRCPATH}/AmqpSender.java ${SRCPATH}/AmqpReceiver.java  ${SRCPATH}/JmsSenderShim.java ${SRCPATH}/JmsReceiverShim.java
jar -cf ${TARGETPATH}/qpid-jms-shim.jar -C ${TARGETPATH}/classes ${BASEPATH}/AmqpSender.class -C ${TARGETPATH}/classes ${BASEPATH}/AmqpSender\$1.class -C ${TARGETPATH}/classes ${BASEPATH}/AmqpSender\$MyExceptionListener.class -C ${TARGETPATH}/classes ${BASEPATH}/AmqpReceiver.class -C ${TARGETPATH}/classes ${BASEPATH}/AmqpReceiver\$1.class -C ${TARGETPATH}/classes ${BASEPATH}/AmqpReceiver\$MyExceptionListener.class  -C ${TARGETPATH}/classes ${BASEPATH}/JmsSenderShim.class -C ${TARGETPATH}/classes ${BASEPATH}/JmsSenderShim\$1.class -C ${TARGETPATH}/classes ${BASEPATH}/JmsSenderShim\$MyExceptionListener.class -C ${TARGETPATH}/classes ${BASEPATH}/JmsReceiverShim.class -C ${TARGETPATH}/classes ${BASEPATH}/JmsReceiverShim\$1.class -C ${TARGETPATH}/classes ${BASEPATH}/JmsReceiverShim\$MyExceptionListener.class
