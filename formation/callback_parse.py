###############################################################
##                    Module author info                     ##
##                                                           ##
## email:    kavyanshkhaitan11@gmail.com                     ##
## phone:    +91 7990617889                                  ##
## github:   KavyanshKhaitan2                                ##
##                                                           ##
## Issue: #32                                                ##
##    https://github.com/ObaraEmmanuel/Formation/issues/32   ##
###############################################################

import typing

STRING_DELIMETERS = ['"', "'"]

def isValidArg(arg:str) -> str:
    """Checks if an argument is valid.

    Args:
        arg (str): Raw argument to check.

    Returns:
        bool: Is the argument valid?
    """
    if not arg: return False
    
    for x in STRING_DELIMETERS:
        if [arg[0], arg[-1]] == [x, x]:
            return True
    if [arg[0] not in STRING_DELIMETERS, arg[-1] not in STRING_DELIMETERS] == [True, True]:
        return True
    if arg.find('=') != -1:
        eqpos = arg.find('=')
        value = arg[eqpos+1:]
        if isValidArg(value):
            return True
    return False

def processArg(arg:str, parsedCommandList:list[str], commandKwargs:dict[str, typing.Any]):
    """Process an argument. Dependency of `parse` method.

    Args:
        `arg (str) : . . . . . . . . . `Raw argument in string to parse.
        `parsedCommandList (list): . . `List of parsed raw arguments in strings. (WILL be modified!)
        `commandKwargs (dict): . . . . `List of parsed raw keyword arguments in strings. (WILL be modified!)
    """
    if arg.find("=") != -1:
        inString = 0
        for char in arg:
            if char in STRING_DELIMETERS:
                inString = 1 - inString
            if char == "=":
                break
        if not inString:
            eqpos = arg.find("=")
            key = arg[:eqpos]
            value = arg[eqpos+1:]
            
            commandKwargs[key] = value
            return
    parsedCommandList.append(arg)

def parse(command:str):
    """Returns parts of a command after parsing it using eval method.

    Args:
        `command (str): . . ` command string.
    
    Command String Syntax:
    	`funcname 1 "arg2" kwarg1="hello" kwarg2="world!"`

    Returns:
        `commandFunc (str) : . . . . `name of the function.
        `commandArgs (list): . . . . `values of regular arguments.
        `commandKwargs (dict): . . . `values of kwargs.
        `parsedCommandList (list): . `values of raw parse.
    """
    commandList = command.split(' ')
    commandKwargs = {}
    parsedCommandList = []
    currentArg = ""
    for part in commandList:
        if not isValidArg(part):
            currentArg += (" " if currentArg else "") + part
            
            if isValidArg(currentArg):
                processArg(currentArg, parsedCommandList, commandKwargs)
                currentArg = ""
            continue
        else:
            currentArg = ""
        processArg(part, parsedCommandList, commandKwargs)

    commandFunc:str = parsedCommandList[0]
    commandArgs:list = parsedCommandList[1:]
    commandArgs = [eval(x) for x in commandArgs]

    for key, value in commandKwargs.items():
        commandKwargs[key] = eval(value)
    return commandFunc, commandArgs, commandKwargs, parsedCommandList

# if __name__ == "__main__":
#     command = "btn 1"
#     output = parse(command)
#     commandFunc, commandArgs, commandKwargs, parsedCommandList = output
#     print(f"{parsedCommandList = }")
#     print(f"{commandKwargs = }")
#     print(f"{commandArgs = }")
#     print(f"{commandFunc = }")

