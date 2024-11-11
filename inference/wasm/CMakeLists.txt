add_executable(bergamot-translator
    bindings/service_bindings.cpp
    bindings/response_options_bindings.cpp
    bindings/response_bindings.cpp
)

# Generate version file that can be included in the wasm artifacts
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/project_version.js.in
               ${CMAKE_CURRENT_BINARY_DIR}/project_version.js @ONLY)

# This header inclusion needs to go away later as path to public headers of bergamot
# translator should be directly available from "bergamot-translator-source" target
target_include_directories(bergamot-translator
    PRIVATE ${CMAKE_SOURCE_DIR}/src/translator
    PRIVATE ${CMAKE_SOURCE_DIR}
)

# This compile definition is required for generating binding code properly
target_compile_definitions(bergamot-translator PRIVATE WASM_BINDINGS)
target_compile_options(bergamot-translator PRIVATE ${WASM_COMPILE_FLAGS})
target_link_options(bergamot-translator PRIVATE ${WASM_LINK_FLAGS})
target_link_options(bergamot-translator PRIVATE --extern-pre-js=${CMAKE_CURRENT_BINARY_DIR}/project_version.js)

set_target_properties(bergamot-translator PROPERTIES
                        SUFFIX ".js"
                        RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
                      )

target_link_libraries(bergamot-translator bergamot-translator-source)
