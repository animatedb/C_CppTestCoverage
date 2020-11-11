# This file instruments c or c++ code to generate code coverage information.
# When the instrumented c or c++ code runs, it will write the output to
# a file. Then covStats.py is run, which takes the output data and produces
# organized info inluding coverage percentages and source code with comments
# that indicate coverage.
import os
import shutil
import re
import cCovDefinitions
from typing import List

HighestInstrLineIndex = 0
InstrLineIndex = 0

# Copy from a project source directory and instrument the source files. 
def covInstr() -> None:
    fileCount = 0
    for src in cCovDefinitions.srcPaths:
        fileCount = covInstrFiles(src, fileCount)
    cCovSourcePath = cCovDefinitions.cCovSourcePath
    print('Processed ' + str(fileCount) + ' source files.')
    outputCoverageHeader(cCovSourcePath, fileCount, HighestInstrLineIndex)
    outputCoverageArray(cCovSourcePath, fileCount, HighestInstrLineIndex)
    # Make a path for the instrumented counts.
    path = os.path.join(os.path.dirname(__file__), cCovDefinitions.outPath)
    makePath(path)


# Instrument every file ending with certain extensions in the srcPath.
# Simply copy all other files such as project files.
def covInstrFiles(srcPath:str, fileCount:int) -> None:
    dirName = os.path.dirname(__file__)
    rootPath = os.path.join(cCovDefinitions.sourceRoot, srcPath)
    print('Scanning', rootPath)
    for (dirPath, dirNames, fileNames) in os.walk(rootPath):
        for srcFn in fileNames:
            fullSrcPath = os.path.join(dirName, dirPath, srcFn)
            relSrcPath = fullSrcPath[len(dirName+'/')+len(cCovDefinitions.sourceRoot):]
            instrPath = os.path.join(dirName, cCovDefinitions.coverageRoot, relSrcPath)
            instrFile, copyFile = cCovDefinitions.filterFiles(fullSrcPath)
            if instrFile:
                covInstrSourceFile = CovInstrSourceFile()
                covInstrSourceFile.process(fullSrcPath, instrPath, fileCount)
                fileCount += 1
                print(fileCount, os.path.normpath(fullSrcPath))
            elif copyFile:
                # If the target was modified, don't copy
                if not os.path.exists(instrPath) or \
                    os.path.getmtime(fullSrcPath) > os.path.getmtime(instrPath):
                    makePath(instrPath)
                    shutil.copyfile(fullSrcPath, instrPath)
    return fileCount

class OutputInstrFile:
    def __init__(self, srcPath, instrPath:str) -> None:
        makePath(instrPath)
        # @todo - look at something to see if # lines changed
        if True:
##        if not os.path.exists(instrPath) or \
##            os.path.getmtime(srcPath) > os.path.getmtime(instrPath):
            self.outf = open(instrPath, 'w')
            dirName = os.path.dirname(__file__)
            incPath = os.path.normpath(os.path.join(dirName,
                cCovDefinitions.coverageHeader))
            incStr = '#include \"' + incPath + '\"\n'
            self.outf.write(incStr)
        else:
            self.outf = None

    def __del(self):
        self.outf.close()

    def write(self, text:str) -> None:
        if self.outf:
            self.outf.write(text)

# Instrument a source file by copying to an output directory.
# This does not do any comment or preproc parsing.
# This uses a very simple rule to determine if the braces are in a
# statement initialization. It only checks the previous line for ending with '='
class CovInstrSourceFile:
    def process(self, srcPath:str, instrPath:str, fileIndex:int) -> None:
        global InstrLineIndex
        InstrLineIndex = 0
        with open(srcPath, 'r') as inFile:
            self.fileIndex = fileIndex
            self.srcPath = srcPath
            self.braceLevel = 0
            self.startDataBraceLevel = 0
            self.inData = False
            self.outFile = OutputInstrFile(srcPath, instrPath)
            self.lineNum = 0
            prevCodeLine = ''
            for origLine in inFile:
                self.lineNum += 1
                # Strip out comments and insert special code
                commentStartPos = origLine.find("//")
                if commentStartPos != -1:
                    origLine = origLine[0:commentStartPos] + "\n"
                    insertCodePos = origLine.find('cCov:')
                    if insertCodePos != -1:
                        origLine = origLine[insertCodePos + len('cCov:'):]
                # Splits braces into separate lines, etc.
                for codeLine in self.normalizeCode(prevCodeLine, origLine):
                    self.processCodeLine(prevCodeLine, codeLine)
                    prevCodeLine = origLine
            if self.braceLevel != 0:
                print('Brace count error: ' + srcPath, self.braceLevel,
                    'Look at or compile output file to verify.')

    # Make sure there is a brace on the next line after every conditional.
    def normalizeCode(self, prevCode:str, code:str) -> List[str]:
        # Add braces to conditionals with single statement (no braces) on same line.
        if checkSingleLineConditionalSingleStatement(prevCode, code):
            level, insertIndex = findSingleLineConditionalEnd(code)
            if insertIndex == -1:
                insertIndex = 0
            lines = [code[:insertIndex], '\n{ ', code[insertIndex:], '}\n']
        # Add braces to conditionals with single statement (no braces) on next line.
        elif checkMultiLineConditionalSingleStatement(prevCode, code):
            lines = ['{ ', code, '}\n']
        else:
            inc = code.count('{')
            if inc > 1:
                lines = code.split('{')
                if len(lines) > 1:
                    lineCnt = len(lines)
                    for i in range(0, lineCnt):
                        if i != 0:
                            lines[i] = '{' + lines[i]
                        # Don't add a cr to the last line.
                        if i != lineCnt-1:
                            lines[i] = lines[i] + '\n'
                else:
                    lines = [code]
            else:
                lines = [code]
        return lines

    def processCodeLine(self, prevCodeLine:str, codeLine:str) -> None:
        inc = codeLine.count('{')
        dec = codeLine.count('{')
        self.braceLevel += inc
        if self.inData and self.braceLevel == self.startDataBraceLevel:
            self.inData = False

        if checkDataDefStart(prevCodeLine, codeLine):
            self.startDataBraceLevel = self.braceLevel
            self.inData = True

        # If this line has open brace and prev line has switch, then
        # don't instrument current brace level.
        # This pattern attempts to avoid some casts.
        allowBraceInstr = True
        if re.search(r'(^|[^A-Za-z_<\(])(class|struct|switch)([^A-Za-z_]|$)', prevCodeLine):
            allowBraceInstr = False

        if not self.inData and allowBraceInstr:
            # Instrument any open braces that are in code and not in data statements.
            if inc:
                codeLine = instrExistingLine(codeLine, codeLine.index('{')+1, self.fileIndex)
            elif checkInstrCaseDefault(codeLine):
                codeLine = instrExistingLine(codeLine, codeLine.rindex(':')+1, self.fileIndex)
        self.braceLevel -= dec
        self.outFile.write(codeLine)


def checkDataDefStart(prevLine:str, codeLine:str) -> bool:
    startData = False
    regDataPat = '((^|[^A-Za-z_])enum([^A-Za-z_]|$))'
    # If this line has open brace and prev line ended with '=', or
    # This or prev line contains a data start keyword, then
    # don't instrument any nested braces.
    if prevLine.rstrip().endswith('=') or \
        re.search(r'=\s{', codeLine) or \
        re.search(r'typedef\s[\sA-Za-z_]+{', codeLine) or \
        re.search(regDataPat, codeLine) or \
        re.search(regDataPat, prevLine):
        startData = True
    return startData


def checkSingleLineConditionalSingleStatement(prevLine:str, line:str) -> bool:
    instrSingleLine = False
    if ((re.search('(^|\s)(if|for|while)\s*\(', prevLine) or \
        re.search('\selse\s*', prevLine)) and   \
        prevLine.count('{') == 0):
        if(line.count(';') and line.count('{') == 0):
            instrSingleLine = True
        if(re.search('\sfor\s*\(', prevLine) and prevLine.count(';') != 2):
            instrSingleLine = False
    return instrSingleLine
#    if(re.search('(^|\s)(if|for|while)\s*\(', prevLine)):
#        index = findSingleLineConditionalEnd(line)
#        if index > 0 and re.search(';', line[index:]) and line.count('{') == 0:
#            return True
#    return False

def checkMultiLineConditionalSingleStatement(prevLine:str, line:str) -> bool:
    isSingle = False
    if(re.search(r'(^|\s)(if|for|while)\s*\(', prevLine)):
        if line.count('{') == 0 and not str.isspace(line):
            level, pos = findSingleLineConditionalEnd(prevLine)
            if level==0:
                isSingle = True
    return isSingle

# Return: If level==0, then close paren was found, and pos has the position
# after the conditional.
# This must return level!=0 since end paren was not found:   "(foo()"
def findSingleLineConditionalEnd(line):
    level = 0
    pos = -1
    for i in range(0, len(line)):
        if(line[i] == '('):
            level+=1
        elif(line[i] == ')'):
            level-=1
            if(level == 0):
                pos = i+1
                break
    return level, pos

def checkInstrConditionalAndSingleLineStatement(prevLine, line):
    instrSingleLine = False
    if ((re.search(r'(^|\s)(if|for|while)\s*\(', prevLine) or \
        re.search(r'\selse\s*', prevLine)) and   \
        prevLine.count('{') == 0):
        if(line.count(';') and line.count('{') == 0):
            instrSingleLine = True
        if(re.search(r'\sfor\s*\(', prevLine) and prevLine.count(';') != 2):
            instrSingleLine = False
    return instrSingleLine

def checkInstrCaseDefault(line):
    return (re.search(r'case[^A-Za-z_].*:', line) or re.search(r'default\s*:', line))

def instrExistingLine(codeLine, insertIndex, fileIndex):
    global HighestInstrLineIndex
    global InstrLineIndex
    codeLine = codeLine[:insertIndex] + \
        "COV_IN(" + str(fileIndex) + "," + str(InstrLineIndex) + ")" + \
        codeLine[insertIndex:]
    InstrLineIndex += 1
    if InstrLineIndex > HighestInstrLineIndex:
        HighestInstrLineIndex = InstrLineIndex
    return codeLine

def makePath(path:str) -> None:
    dirName = os.path.dirname(path)
    if not os.path.exists(dirName):
        os.makedirs(dirName)

def outputCoverageHeader(coverageSrcPath, numFiles, maxLines):
    outf = open(coverageSrcPath + '/coverage.h', 'w')
    outf.write('// This file is automatically generated.\n')
    outf.write('#pragma once\n')
    outf.write('#define _CRT_SECURE_NO_WARNINGS\n');
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
        "static void cov_read()\n" \
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
        "             fscanf(fp, \"\\%u%*[^\\n]\", &val);\n" \
	"          fscanf(fp, \"%u\", &val);\n" \
        "          gCoverage[fi][li] += val;\n" \
        "          }\n" \
	"        }\n"   \
	"      }\n" \
	"    fclose(fp);\n"   \
	"    }\n"   \
        "  }\n" \
        "static void cov_write()\n" \
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
	"  cov_read();\n" \
	"  cov_write();\n" \
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
