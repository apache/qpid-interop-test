#! /bin/bash

RH_CORE_DIR=${HOME}/RedHat/rh-core
LOCAL_INSTALL_DIR=${HOME}/RedHat/cicd/jenkins-qit/install
PROTON_DIR=${RH_CORE_DIR}/install/lib64/cmake/Proton
PROTONCPP_DIR=${RH_CORE_DIR}/install/lib64/cmake/ProtonCpp
RHEA_DIR=${RH_CORE_DIR}/rhea

if [ -z ${JAVA_HOME} ]; then
    export JAVA_HOME=$(dirname $(dirname $(alternatives --display javac | grep 'javac' | grep 'link' | awk '{print $NF}')))
fi
echo "JAVA_HOME=${JAVA_HOME}"

if [ -d build ]; then
    if [ -d build.old ]; then
        rm -rf build.old
    fi
    mv build build.old
fi
mkdir build
cd build

cmake -DProton_DIR=${PROTON_DIR} -DProtonCpp_DIR=${PROTONCPP_DIR} -DRHEA_DIR=${RHEA_DIR} -DCMAKE_INSTALL_PREFIX=${LOCAL_INSTALL_DIR}  ..
make install

cd ..
