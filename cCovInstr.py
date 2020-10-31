# This file instruments c or c++ code to generate code coverage information.
# When the instrumented c or c++ code runs, it will write the output to
# a file. Then covStats.py is run, which takes the output data and produces
# organized info inluding coverage percentages and source code with comments
# that indicate coverage.
import os
import shutil
import re
import cCovDefinitions

HighestInstrLineIndex = 0
FileNum = 0
InstrLineIndex = 0
DisplayWarnings = False

# Copy from a project source directory and instrument the source files. 
def covInstr() -> None:
    global FileNum
    for src in cCovDefinitions.srcPaths:
        covInstrFiles(src)
    cCovSourcePath = cCovDefinitions.cCovSourcePath
    print('Processed ' + str(FileNum) + ' source files.')
    outputCoverageHeader(cCovSourcePath, FileNum, HighestInstrLineIndex)
    outputCoverageArray(cCovSourcePath, FileNum, HighestInstrLineIndex)
    # Make a path for the instrumented counts.
    path = os.path.join(os.path.dirname(__file__), cCovDefinitions.outPath)
    makePath(path)


# Instrument every file ending with certain extensions in the srcPath.
# Simply copy all other files such as project files.
def covInstrFiles(srcPath:str) -> None:
    global FileNum
    dirName = os.path.dirname(__file__)
    for (dirPath, dirNames, fileNames) in os.walk(cCovDefinitions.sourceRoot+srcPath):
        for srcFn in fileNames:
            fullSrcPath = os.path.join(dirName, dirPath, srcFn)
            relSrcPath = fullSrcPath[len(dirName+'/')+len(cCovDefinitions.sourceRoot):]
            instrPath = os.path.join(dirName, cCovDefinitions.coverageRoot, relSrcPath)
            instrFile, copyFile = cCovDefinitions.filterFiles(fullSrcPath)
            if instrFile:
                covInstrSourceFile(fullSrcPath, instrPath, FileNum)
                FileNum += 1
                print(FileNum, os.path.normpath(fullSrcPath))
            elif copyFile:
                # If the target was modified, don't copy
                if not os.path.exists(instrPath) or \
                    os.path.getmtime(fullSrcPath) > os.path.getmtime(instrPath):
                    makePath(instrPath)
                    shutil.copyfile(fullSrcPath, instrPath)


# Instrument a source file by copying to an output directory.
# This does not do any comment or preproc parsing.
# This uses a very simple rule to determine if the braces are in a
# statement initialization. It only checks the previous line for ending with '='
def covInstrSourceFile(srcPath:str, instrPath:str, fileNum:int) -> None:
    global InstrLineIndex
    InstrLineIndex = 0
    braceLevel = 0
    lineNum = 0
    startInStatementLevel = 0
    inStatement = False
    # Indicates whether to add instrumentation for a brace. For example, if
    # it is data initialization, then instrumentation should not be added.
    allowBraceInstr = True
    inStructOrSwitch = False
    inf = open(srcPath, 'r')

    makePath(instrPath)
    if not os.path.exists(instrPath) or \
        os.path.getmtime(srcPath) > os.path.getmtime(instrPath):
        outf = open(instrPath, 'w')
        dirName = os.path.dirname(__file__)
        incPath = os.path.normpath(os.path.join(dirName,
            cCovDefinitions.coverageHeader))
        incStr = '#include \"' + incPath + '\"\n'
        outf.write(incStr)
    else:
        outf = None
    prevLine = ""
    for origLine in inf:
        allowBraceInstr = True
        codeLine = origLine  # codeLine does not contain comment lines. "//"
        outLine = origLine
        commentStartPos = origLine.find("//")
        if commentStartPos != -1:
            codeLine = origLine[0:commentStartPos] + "\n"
            insertCodePos = origLine.find('cCov:')
            if insertCodePos != -1:
                outLine = origLine[insertCodePos + len('cCov:'):]
        lineNum += 1
        if braceLevel == startInStatementLevel:
            inStatement = False
        inc = codeLine.count('{')
        dec = codeLine.count('}')
        if(checkSingleLineConditionalAndStatement(codeLine)):
            outLine = instrExistingLinePlusBraces(codeLine, \
                findSingleLineConditionalEnd(codeLine), fileNum)
            instrSingleLine = False
        else:
            instrSingleLine = checkInstrConditionalAndSingleLineStatement(prevLine, codeLine)
        # Check to see how many braces are on a single line. If there is "{ code }", then
        # allow it, and prevent adding any extra instrumentation. Otherwise generate an error.
        if(inc + dec > 1):
            if(re.match('^\s*\{.*\}\s*$', codeLine) and not prevLine.rstrip().endswith(',')):
                outLine = instrExistingLine(codeLine, codeLine.index('{')+1, fileNum)
            elif DisplayWarnings:
                print("Too many braces on a line: " + srcPath, lineNum, codeLine)
            allowBraceInstr = False       # Prevent brace instrumentation below
        if dec:
            braceLevel -= dec
        if instrSingleLine:
            if outf:
                outf.write("{\n")
            instrNewLine(outf, fileNum)
        if checkInstrCaseDefault(codeLine):
            # It could be a namespace name like "case foo::bar:"
            outLine = instrExistingLine(codeLine, codeLine.rindex(':')+1, fileNum)
        if outf:
            outf.write(outLine)
        if instrSingleLine:
            if outf:
                outf.write("}\n")
        if inc:
            braceLevel += inc
            regDataPat = '(^|[^A-Za-z_])enum([^A-Za-z_]|$)'
            # If this line has open brace and prev line ended with '=', or
            # This or prev line contains a data start keyword, then
            # don't instrument any nested braces.
            if prevLine.rstrip().endswith("=") or re.search(regDataPat, codeLine) or \
                re.search(regDataPat, prevLine):
                inStatement = True
                startInStatementLevel = braceLevel-1
            # If this line has open brace and prev line has switch, then
            # don't instrument current brace level.
            # This pattern attempts to avoid some casts.
            if re.search('(^|[^A-Za-z_<\(])(class|struct|switch)([^A-Za-z_]|$)', prevLine):
                allowBraceInstr = False
            # Discard some common data declarations
            if not inStatement and allowBraceInstr:
                instrNewLine(outf, fileNum)
        prevLine = codeLine
    inf.close()
    if outf:
        outf.close()
    if braceLevel != 0:
        print('Brace count error: ' + srcPath + ' ' + str(braceLevel) + \
            ' Look at or compile output file to verify.')

def checkSingleLineConditionalAndStatement(line):
    if(re.search('(^|\s)(if|for|while)\s*\(', line)):
        index = findSingleLineConditionalEnd(line)
        if(index > 0 and re.search(';', line[index:])):
            return True
    return False

def findSingleLineConditionalEnd(line):
    nest = 0
    opened = False
    for i in range(0, len(line)):
        if(line[i] == '('):
            opened = True
            nest+=1
        elif(line[i] == ')' and opened):
            nest-=1
            if(nest == 0):
                return i+1
    return 0

def checkInstrConditionalAndSingleLineStatement(prevLine, line):
    instrSingleLine = False
    if ((re.search('(^|\s)(if|for|while)\s*\(', prevLine) or \
        re.search('\selse\s*', prevLine)) and   \
        prevLine.count('{') == 0):
        if(line.count(';') and line.count('{') == 0):
            instrSingleLine = True
        if(re.search('\sfor\s*\(', prevLine) and prevLine.count(';') != 2):
            instrSingleLine = False
    return instrSingleLine

def checkInstrCaseDefault(line):
    return (re.search('case[^A-Za-z_].*:', line) or re.search('default\s*:', line))

def instrNewLine(outf, fileNum):
    global InstrLineIndex
    if outf:
        outf.write("COV_IN(" + str(fileNum) + "," + str(InstrLineIndex) + ")\n")
    instrLine(fileNum)

def instrExistingLinePlusBraces(codeLine, insertIndex, fileNum):
    global InstrLineIndex
    codeLine = codeLine[:insertIndex] + \
        "{ COV_IN(" + str(fileNum) + "," + str(InstrLineIndex) + ")" + \
        codeLine[insertIndex:] + "}\n"
    instrLine(fileNum)
    return codeLine

def instrExistingLine(codeLine, insertIndex, fileNum):
    global InstrLineIndex
    codeLine = codeLine[:insertIndex] + \
        "COV_IN(" + str(fileNum) + "," + str(InstrLineIndex) + ")" + \
        codeLine[insertIndex:]
    instrLine(fileNum)
    return codeLine

def instrLine(fileNum):
    global HighestInstrLineIndex
    global InstrLineIndex
    InstrLineIndex += 1
    if InstrLineIndex > HighestInstrLineIndex:
        HighestInstrLineIndex = InstrLineIndex

def makePath(path:str) -> None:
    dirName = os.path.dirname(path)
    if not os.path.exists(dirName):
        os.makedirs(dirName)

def outputCoverageHeader(coverageSrcPath, numFiles, maxLines):
    outf = open(coverageSrcPath + '/coverage.h', 'w')
    outf.write('// This file is automatically generated.\n')
    outf.write('#pragma once\n')
    outf.write('extern ' + cCovDefinitions.coverageCounterType + \
        ' gCoverage[' + str(numFiles) + '][' + str(maxLines) + '];\n')
    outf.write('#define COV_IN(fileIndex, lineIndex) gCoverage[fileIndex][lineIndex]++;\n')
    outf.write('void update_coverage();\n')
    outf.close()
    
def outputCoverageArray(coverageSrcPath, numFiles, maxLines):
    dirName = os.path.dirname(__file__)
    statsFn = os.path.join(dirName, cCovDefinitions.coverageStatsPath).replace(os.sep, '/')
    coverageCPath = coverageSrcPath + '/coverage.c'
    outf = open(coverageCPath, 'w')
    outf.write('// This file is automatically generated\n')
    outf.write(cCovDefinitions.coverageCounterType + ' gCoverage[' + \
        str(numFiles) + '][' + str(maxLines) + '];\n')
    lines = "#define _CRT_SECURE_NO_WARNINGS\n" \
        "#include <stdio.h>\n" \
        "void read()\n" \
        "  {\n"   \
        "  FILE *fp = fopen(\"" + statsFn + "\", \"r\");\n" \
	"  if(fp)\n"    \
	"    {\n"   \
	"    int maxLines = 0;\n"   \
	"    int numFiles = 0;\n"   \
	"    fscanf(fp, \"%d%*[^\\n]\", &numFiles);\n"    \
	"    fscanf(fp, \"%d%*[^\\n]\", &maxLines);\n"    \
	"    if(numFiles == " + str(numFiles) + " && maxLines == " + str(maxLines) + ")\n"   \
	"      {\n" \
	"      for(int fi=0; fi<" + str(numFiles) + "; fi++)\n" \
	"        {\n"   \
	"        for(int li=0; li<" + str(maxLines) + "; li++)\n"    \
	"          {\n" \
        "          unsigned int val;\n" \
        "          if(li == 0)    // discard file index\n" \
        "             fscanf(fp, \"\%u%*[^\\n]\", &val);\n" \
	"          fscanf(fp, \"%u\", &val);\n" \
        "          gCoverage[fi][li] += val;\n" \
        "          }\n" \
	"        }\n"   \
	"      }\n" \
	"    fclose(fp);\n"   \
	"    }\n"   \
        "  }\n" \
        "void write()\n" \
	"  {\n" \
	"  FILE *fp = fopen(\"" + statsFn + "\", \"w\");\n"   \
	"  fprintf(fp, \"%d   # Number of files\\n\", " + str(numFiles) + ");\n"  \
	"  fprintf(fp, \"%d   # Max number of instrumented lines per file\\n\", " + str(maxLines) + ");\n"  \
	"  for(int fi=0; fi<" + str(numFiles) + "; fi++)\n" \
        "    {\n"   \
	"    for(int li=0; li<" + str(maxLines) + "; li++)\n"    \
        "      {\n"   \
	"        if(li == 0)  // add file index for reference (not used)\n" \
	"          fprintf(fp, \"%d   # File Index\\n\", fi);\n" \
	"        fprintf(fp, \"%u\", gCoverage[fi][li]);\n" \
        "        fprintf(fp, \"\\n\");\n" \
	"      }\n"   \
	"    }\n"   \
	"  fclose(fp);\n"   \
	"  }\n"   \
        "void update_coverage()\n" \
	"  {\n" \
	"  read();\n" \
	"  write();\n" \
	"  }\n"
# This code only works for C++ and does not appear to work reliably with MSVC.
#        "struct CoverageUpdater {\n" \
#        "  ~CoverageUpdater()\n" \
#        "    { update_coverage(); }\n" \
#        "  };\n" \
#        "CoverageUpdater gCov;"

    outf.write(lines)
    outf.close()
    coverageCppPath = coverageCPath + 'pp'
    shutil.copyfile(coverageCPath, coverageCppPath)

if __name__ == '__main__':
    covInstr()
