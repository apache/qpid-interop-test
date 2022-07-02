project(qpid-interop-test-fe2o3-amqp-shims-amqp-types-test)

cmake_minimum_required(VERSION 3.16.3 FATAL_ERROR)

set(CARGO_BUILD_ROOT ${CMAKE_CURRENT_BINARY_DIR})
set(MAKE_INSTALL_ROOT
    ${CMAKE_INSTALL_PREFIX}/libexec/qpid_interop_test/shims/fe2o3-amqp/amqp_types_test)

install(
    CODE "EXECUTE_PROCESS (
        COMMAND cargo +${RUST_TOOLCHAIN} install --path ./ --target-dir ${CARGO_BUILD_ROOT} --root ${MAKE_INSTALL_ROOT}
        COMMAND chmod +x ${MAKE_INSTALL_ROOT}/bin/Sender ${MAKE_INSTALL_ROOT}/bin/Receiver
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        )"
)
