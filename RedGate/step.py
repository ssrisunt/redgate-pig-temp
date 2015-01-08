from abc import ABCMeta, abstractmethod
# from codeGenTable import codeGenTable
from moduleLoader import ModuleLoader


class Binder:
    @staticmethod
    def bindParams(script, paramsDic):
        for key, value in paramsDic.iteritems():
            script = script.replace('$' + key, value)

        return script


class BaseStep(object):
    __metaclass__ = ABCMeta

    TYPE_OPERATOR = "op"
    TYPE_MODULE = "md"
    mType = None
    mData = None
    mStepId = -1
    outAliase = None
    outFieldsList = None

    @abstractmethod
    def codeGen(self):
        pass

    def getOutAliase(self):
        if self.outAliase is None:
            raise Exception("OutAliase is None: " + str(self.getId))
        else:
            return self.outAliase

    def getOutFieldsList(self):
        if self.outFieldsList is None:
            raise Exception("OutFieldsLis is None: " + str(self.getId))
        else:
            return self.outFieldsList

    def getOutFieldsListString(self, withType=True):
        out = ""
        for i in self.outFieldsList:
            if not withType:
                i = i[:i.rfind(":")]
            out += i
            out += ", "

        return out.rstrip(", ")
#    @abstractmethod
#    def getOutAliase(self):
#        pass

    def setId(self, id):
        self.mStepId = id

    def getId(self):
        return self.mStepId


class BinaryOperatorStep(BaseStep):
    moduleName = "BinOP"
    templateCodeGenString = "$ThisOut = $Operator $Operand1 BY \
$OnField, $Operand2 BY $OnField;\n"
    operator = None
    operationOn = None
    # outAliase = None # defined in super class
    # left/rigth hand side step
    lhs = None
    rhs = None
    # outFieldsList = None   # defined in super class

    def __init__(self, operator, operationOn, lhs, rhs):
        self.mType = BaseStep.TYPE_OPERATOR

        self.operator = operator
        self.operationOn = operationOn

        # TODO support more binOP
        self.outAliase = "JoinResult"

        self.lhs = lhs
        self.rhs = rhs

    def codeGen(self):
        # handling generated code
        lhsOut = self.lhs.codeGen()
        rhsOut = self.rhs.codeGen()
        params = {"Operator": self.operator,
                  "OnField": self.operationOn,
                  "Operand1": self.lhs.getOutAliase(),
                  "Operand2": self.rhs.getOutAliase(),
                  "ThisOut": self.outAliase}
        genString = lhsOut + rhsOut
        genString += Binder.bindParams(self.templateCodeGenString, params)
        genString += "\n\n"

        # handling fields
        lhsOutFields = self.lhs.getOutFieldsList()[:]
        rhsOutFields = self.rhs.getOutFieldsList()[:]
        # TODO use module type to compare
        if self.lhs.moduleName != "BinOP":
            for i in xrange(len(lhsOutFields)):
                lhsOutFields[i] = self.lhs.moduleName + "::" + lhsOutFields[i]
        if self.rhs.moduleName != "BinOP":
            for i in xrange(len(rhsOutFields)):
                rhsOutFields[i] = self.rhs.moduleName + "::" + rhsOutFields[i]

        self.outFieldsList = lhsOutFields + rhsOutFields

        genString += self.genFormatStatement()

        # print outString
        # print "\n\n"
        return genString

    def genFormatStatement(self):
        opOn = self.lhs.outAliase + "::" + self.operationOn
        opOnString = opOn + " AS " + self.operationOn
        outString = self.outAliase + " = FOREACH " + self.outAliase + \
            " GENERATE " + opOnString + ", * AS (" + \
            self.getOutFieldsListString() + ");\n"

        # below handles duplicate operationOn key
        self.outFieldsList = [self.operationOn + ":chararray"] + self.outFieldsList

        newOutList = self.outFieldsList[:1]
        for i in self.outFieldsList[1:]:
            if self.operationOn not in i:
                newOutList.append(i)
        self.outFieldsList = newOutList

        outString += self.outAliase + " = FOREACH " + self.outAliase + \
            " GENERATE " + self.getOutFieldsListString(withType=False) + ";\n\n"
        print "---------------------------"
        print self.outFieldsList
        print newOutList
        print "---------------------------"
        return outString


class ModuleStep(BaseStep):
    params = None
    moduleName = None
    # outAliase = None # defined in super class
    outFields = None
    templateCodeGenString = ""

    def __init__(self, moduleName, params):
        self.mType = BaseStep.TYPE_MODULE
        self.moduleName = moduleName
        self.params = params
        # self.templateCodeGenString = codeGenTable[moduleName]
        moduleData = ModuleLoader.loadModule("moduleFile/" +
                                             moduleName + ".md")
        if moduleData is None:
            raise Exception("ERROR: ModuleLoader returns None")
        if moduleData["moduleName"] != self.moduleName:
            raise Exception("ERROR: ModuleName ERROR")
        self.outAliase = moduleData["outAliase"]
        self.outFields = moduleData["outFields"]

        self.outFieldsList = self.outFields
#        for i in self.outFields:
#            self.outFieldsList.append(moduleName + "::" + i)

        self.templateCodeGenString = moduleData["templateCode"]

    def codeGen(self):

        genString = Binder.bindParams(self.templateCodeGenString, self.params)
        genString += "\n"
        genString += self.genFormatStatement()

        # print outString

        # print formatStatement

        genString += "\n\n"
        # print "\n\n"

        return genString

    def genFormatStatement(self):
        outString = self.outAliase + " = FOREACH " + self.outAliase + \
            " GENERATE * AS (" + self.getOutFieldsListString() + ");"
        return outString


if __name__ == "__main__":
    A1params = {"startRow": "48_1025339", "endRow": "48_1025340"}
    Bparams = {"minReqSum": "15"}
    lop = ModuleStep("A1", A1params)
    rop = ModuleStep("B", Bparams)
    binOp = BinaryOperatorStep(operator="JOIN", operationOn="UserId",
                               lhs=lop, rhs=rop)

    rop2 = ModuleStep("C", Bparams)
    binOp2 = BinaryOperatorStep(operator="JOIN", operationOn="UserId",
                                lhs=binOp, rhs=rop2)

    genString = "REGISTER /usr/lib/hbase/lib/*.jar;\n/**/\n"

    genString += binOp2.codeGen()
    # genString += binOp.codeGen()

    genString += "\n\nDUMP JoinResult;"
    # print genString

    with open("outt.pig", "w") as outFile:
        outFile.write(genString)
