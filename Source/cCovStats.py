import os
import cCovDefinitions

HighestInstrLineIndex = 0

def covStats():
    fileNum = 0
    coverage = getCoverage(cCovDefinitions.coverageStatsPath)
    totalHits = 0
    totalInstrLines = 0
    dirName = os.path.dirname(__file__)
    for srcPath in cCovDefinitions.srcPaths:
        for (dirPath, dirNames, fileNames) in os.walk(cCovDefinitions.sourceRoot+srcPath):
            for srcFn in fileNames:
                fullSrcPath = os.path.join(dirName, dirPath, srcFn)
                relSrcPath = fullSrcPath[len(dirName+'/')+len(cCovDefinitions.sourceRoot):]
                instrPath = os.path.normpath(
                    os.path.join(dirName, cCovDefinitions.coverageRoot, relSrcPath))
                instrFile, copyFile = cCovDefinitions.filterFiles(fullSrcPath)
                if instrFile:
                    instrCountFn = os.path.normpath(os.path.join(dirName, cCovDefinitions.outPath,
                        relSrcPath.replace('.', '_')))
                    (numHits, numInstrLines) = covStatsFile(instrPath,
                        instrCountFn, fileNum, coverage)
                    totalHits += numHits
                    totalInstrLines += numInstrLines
                    fileNum += 1
    # This is not the % of lines covered. It is % of hits.
    print('Total:', totalHits, '/', totalInstrLines,
          str(totalHits * 100 / totalInstrLines) + '%')

# This returns the stats for one source file from the coverage stats file.
def getCoverageStatsForFile(fileNum, coverage):
    maxInstrLines = coverage[1]
    covheaderlines = 2
    srcheaderlines = 1
    start = covheaderlines + srcheaderlines + (fileNum * (maxInstrLines + srcheaderlines))
    return coverage[start:start + maxInstrLines]

def covStatsFile(instrSrcFn, countSrcFn, fileNum, coverage):
    srcf = open(instrSrcFn, 'r')
    makePath(countSrcFn)
    dstf = open(countSrcFn+".txt", 'w')
    numInstrLines = 0
    fileStats = getCoverageStatsForFile(fileNum, coverage)
    for line in srcf.readlines():
        if line.count("COV_IN"):
            line = line[0:line.find('\n')]
            line += '\t\t// ' + str(fileStats[numInstrLines]) + '\n'
            numInstrLines += 1
        dstf.write(line)
    srcf.close()
    dstf.close()
    numHits = 0
    for x in fileStats:
        if x != 0:
            numHits += 1
    if numInstrLines != 0:
        percent = numHits * 100 / numInstrLines
    else:
        percent = 100
    print(fileNum,
        instrSrcFn, numHits, numInstrLines, '{0:.2f}'.format(percent) + '%')
    return (numHits, numInstrLines)

# Coverage file format:
# First line is number of files.
# Second line is maximum number of instrumented lines per file.
# Then for every file, the first line is the file index, followed
# by a counter for each instrumented line.
def getCoverage(fn):
    values = []
    f = open(fn, 'r')
    for line in f.readlines():
        tokens = line.split()
        values.append(int(tokens[0]))
    f.close()
    return values

def makePath(path:str) -> None:
    dirName = os.path.dirname(path)
    if not os.path.exists(dirName):
        os.makedirs(dirName)

if __name__ == '__main__':
    covStats()

