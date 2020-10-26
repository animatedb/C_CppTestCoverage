
# Location of all source files.
srcPath = "../Example"
# Location of instrumented files
outDir = "out/"
# Where to put the created coverage source files to compile with the source.
coverageSrcPath = outDir + "Source/CppTestCoverage"
# Location of statistics file - relative to outDir
coverageStatsRelPath = outDir + "Source/CppTestCoverage/coverageStats.txt"

def filterFiles(srcFn):
    useFile = srcFn.endswith(".cpp") or srcFn.endswith(".h")
    return useFile

