import unittest as unittest
import os as os
import subprocess as subproc
#import sys as sys
#sys.path.append("..\Source")

class TestCov(unittest.TestCase):
    def setUp(self):
        self.covOutFn = 'Cov/TestSource/acCovTest.cpp'
#        if os.path.exists(self.covOutFn):
#            os.remove(self.covOutFn)
        # The module path is not set for imports
#        exec(open('../Source/cCovInstr.py').read())

#        subproc.run(['python3', '../Source/cCovInstr.py'])
        
    def testCovInstr(self):
        lineNum = 0
        with open(self.covOutFn, 'r') as instrFile:
            for line in instrFile.readlines():
                lineNum += 1
                if 'REQ_INSTR' in line:
                    if 'COV_IN' not in line:
                        print(lineNum, line)
                        self.assertTrue(False)
                else:
                    if 'COV_IN' in line:
                        print(lineNum, line)
                        self.assertTrue(False)

if __name__ == '__main__':
    unittest.main()
