#!/bin/bash

# JARS
JMS_API=${HOME}/.m2/repository/org/apache/geronimo/specs/geronimo-jms_1.1_spec/1.1.1/geronimo-jms_1.1_spec-1.1.1.jar:${HOME}/.m2/repository/org/apache/qpid/qpid-jms-client/0.4.0-SNAPSHOT/qpid-jms-client-0.4.0-SNAPSHOT.jar
CLASSPATH=${JMS_API}

BASEPATH=org/apache/qpid/interop_test/shim
SRCPATH=src/main/java/${BASEPATH}
TARGETPATH=target

mkdir -p ${TARGETPATH}/classes
javac -cp ${CLASSPATH} -d ${TARGETPATH}/classes ${SRCPATH}/ProtonJmsSender.java ${SRCPATH}/ProtonJmsReceiver.java
jar -cf ${TARGETPATH}/qpid-jms-shim.jar -C ${TARGETPATH}/classes ${BASEPATH}/ProtonJmsSender.class -C ${TARGETPATH}/classes ${BASEPATH}/ProtonJmsSender\$1.class -C ${TARGETPATH}/classes ${BASEPATH}/ProtonJmsSender\$MyExceptionListener.class -C ${TARGETPATH}/classes ${BASEPATH}/ProtonJmsReceiver.class -C ${TARGETPATH}/classes ${BASEPATH}/ProtonJmsReceiver\$1.class -C ${TARGETPATH}/classes ${BASEPATH}/ProtonJmsReceiver\$MyExceptionListener.class
