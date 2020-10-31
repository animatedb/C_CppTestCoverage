# Steps for coverage
# 1. Modify this file to refer to project source directories to copy
#    in order to add instrument to them.
# 2. Modify some source if it cannot be instrumented or exclude it if it is
#    difficult to parse using instrExcludeFilePatterns. Do not change the
#    number of COV_IN statements when editing code.
#    This code mainly works for C or C++ code where the statement is on a different
#    line than the open brace, so it works for some K&R, GNU, Whitesmiths, etc.
#    If the code has another style, it may have to be formatted first, or the
#    parser needs to be modified to split the brace.
# 3. This step is optional. The copied source code can be modified later if desired.
#    The following comments can be added to the original source code so that
#    every time the code is instrumented, the original code will be modified to
#    write the coverage file, and include the coverage code in the project.
#    This should be placed where the program exits.
#       // cCov: update_coverage();
#    The following comment can be used to insert the line in the source.
#    This can be placed in one file outside of any function definition.
#       // cCov: #include "coverage.cpp"
# 4. Run cCovInstr for selected (See srcPaths) projects and instrument the C++ files.
# 5. This step is optional if the original source was modified using the
#    "// cCov:" comments above. Otherwise modify one or multiple points in
#    the instrumented source code to update the count statistics file by calling
#    "update_coverage()". Modify the build projects to compile and link the
#    coverage.cpp or coverage.c in each project. In MSVC, just add the source
#    file to the project.
# 6. Build each instrumented project.
# 7. Make sure the instrumented executables will be run by the tests.
# 8. Run the tests. This will cause the executables to write the instrumented
#    hit counts.
# 9. Run the cCovStats to create a readable file from the hit counts.
# 10. View the coverageStats.txt file or the files in the Out (outPath) directory
#    that contain hit counts for each path in the source files.

# Where to get the source code that will be copied and instrumented.
# This is relative accessed from this python script directory.
sourceRoot = '../Source/'

# Where to put the coverage information.
# This is relative accessed from this python script directory.
coverageRoot = '../Test/Cov/'

# Location of all source files to instrument/measure.
# First tuple is source relative to this Python file.
# Second tuple is where to put the instrumented source so that it can be built.
srcPaths = [
    'Component1',
    'Component2',
    ]

# Location of cCov source (coverage.h and coverage.cpp) that is compiled into project.
# This is relative accessed from this python script directory.
cCovSourcePath = coverageRoot

# Header added to cpp or c source files.
# This is relative accessed from this python script directory.
coverageHeader = coverageRoot + 'coverage.h'

# Location of instrumented output data
# This is relative accessed from this python script directory.
outPath = coverageRoot + 'Out/'

coverageStatsPath = coverageRoot + 'coverageStats.txt'

coverageCounterType = 'unsigned int'

# Add any files that do not need instrumentation or are too difficult to parse here.
instrExcludeFilePatterns = [ 'SQLite.h' ]

# Add any files that do not need to be copied to the coverage build folder here.
copyExcludeFilePatterns = ['.vs', 'x64', '.sdf', '.suo', '.vcxproj.' ]

# This returns whether to instument some source, copy without instrumentation, or to not copy it.
def filterFiles(srcFn):
    instrFileExt = ['.cpp', '.c', '.h']
    instrFile = False
    for ext in instrFileExt:
        instrFile = srcFn.endswith(ext)
        if instrFile:
            break
    for instrPat in instrExcludeFilePatterns:
        if instrPat in srcFn:
            instrFile = False

    copyFile = True
    for exPat in copyExcludeFilePatterns:
        if exPat in srcFn:
            copyFile = False
    return instrFile, copyFile

