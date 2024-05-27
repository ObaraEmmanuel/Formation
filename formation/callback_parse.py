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

def parse_helper(*args, **kwargs):
    return args, kwargs

def parse(command:str):
    """Returns parts of a command after parsing it using eval method.

    Args:
        ``command (str): . . `` command string.
    
    Command String Syntax:
    	``funcname 1 "arg2",kwarg1="hello",kwarg2="world!"``

    Returns:
        ``command_func (str) : . . . . ``name of the function.
        ``command_args (list): . . . . ``values of regular arguments.
        ``command_kwargs (dict): . . . ``values of kwargs.
    """
    command_list:list = command.split(' ')
    command_func: str = command_list[0]
    command_list.pop(0)
    command_string = ""
    for arg in command_list:
        command_string+=(arg+' ')
    command_string.removesuffix(' ')
    args, kwargs = eval(f'parse_helper({command_string})')
    return command_func, args, kwargs

# if __name__ == "__main__":
#     command = "btn 1, 2, 3, 'hello this is a world!', kw1='my kwarg'"
#     output = parse(command)
#     command_func, command_args, command_kwargs = output
#     print(f"{command_kwargs = }")
#     print(f"{command_args = }")
#     print(f"{command_func = }")

