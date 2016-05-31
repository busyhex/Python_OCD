#############################################################################
# OCD_Input : Input class for On Chip Debugger Console
#
# References:
# [1] http://code.activestate.com/recipes/134892/
# [2] http://stackoverflow.com/questions/6179537/python-wait-x-secs-for-a-key-and-continue-execution-if-not-pressed
# [3] rlcompleter — Completion function for GNU readline, https://docs.python.org/2/library/rlcompleter.html
#############################################################################


#############################################################################
# Getch() Implementation
#
# See Ref[1] for more infomation
#############################################################################

class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()
        
class _Getch:
    """Gets a single character from standard input.  Does not echo to the
    screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()        


#############################################################################
# check keyboard hit (non-blocking fashion)
#
# See Ref[2] for more infomation
#############################################################################
    
class _KeyboardHitUnix:
    def __init__(self):
        pass
        
    def __call__(self):
        rlist, wlist, xlist = select([sys.stdin], [], [], 0)
        
        if rlist:
            return True
        else:
            return False
        
class _KeyboardHitWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.kbhit()
    
class _KBHit:

    def __init__(self):
        try:
            self.impl = _KeyboardHitWindows()
        except ImportError:
            self.impl = _KeyboardHitUnix()

    def __call__(self): return self.impl()        
    
    
    
#############################################################################
# OCD_Input : input for On Chip Debugger console
# 
# Remarks:
#  Originally, tab completion can be done through readline package,
#  as illustrated in Ref[3]. But readline package becomes obsolete after
#  Python 3. As an alternative, this class is intended to provide a solution
#  for tab completion in Python 3
#      In addition, to achieve full duplex for serial port while avoiding
#  multi-threading, the input can be handled in a non-blocking fashion by
#  checking the keyboard hit.  
#      Although this class is written as a support class for OCD console,
#  It can be used more generally.
#############################################################################
    
class OCD_Input:
    
    _OCD_INPUT_MAX_LENGTH = 80
    
    #========================================================================
    # __init__
    #
    # Parameter:
    #    prompt: Input prompt, such as ">> "
    #    commands: list of valid commands. This is used by tab completion
    #========================================================================
    
    def __init__ (self, prompt, commands):
        self._getch = _Getch()
        self._kbhit = _KBHit()
        
        self._commands = commands
        self._line = ""
        self._history = []
        self._prompt = prompt
        self.uart_raw_mode_enable = 0
    
    #========================================================================
    # only letter/number and some symbols are allowed
    #========================================================================
    
    def _input_valid (self, ord_c):
        if ( ((ord_c >= ord('0')) and ((ord_c <= ord('9')))) or \
             ((ord_c >= ord('a')) and ((ord_c <= ord('z')))) or \
             ((ord_c >= ord('A')) and ((ord_c <= ord('Z')))) or \
             (ord_c == ord('_')) or \
             (ord_c == ord('.')) or \
             (ord_c == ord('/')) or \
             (ord_c == ord(' ')) ):
             return 1
        else:
             return 0
    
    #========================================================================
    # tab completion based on _commands 
    #========================================================================
    
    def _tab_completion (self):
        match_cmds = [i for i in self._commands if i.startswith (self._line)]
        match_cmds_trimmed = [i[len(self._line):] for i in match_cmds]

        greatest_common_len = 0
        if (len(match_cmds_trimmed)):
            min_len = min([len(i) for i in match_cmds_trimmed])
        else:
            min_len = 0
      
        for i in range(min_len):
            count = 0
            for cmd in match_cmds_trimmed:
                if (cmd[i] == match_cmds_trimmed[0][i]):
                    count = count + 1
     
            if (count == len(match_cmds_trimmed)):
                greatest_common_len = greatest_common_len + 1
            else:
                break
                
        if (greatest_common_len):
            print (match_cmds_trimmed[0][0:greatest_common_len], end="", flush=True)
            return (match_cmds_trimmed[0][0:greatest_common_len])
        else:
            return ("")
    
    #========================================================================
    # use backspace to clear line
    #========================================================================
    
    def _clear_line (self):
        for i in range (OCD_Input._OCD_INPUT_MAX_LENGTH):
            print ("\b \b", end="", flush=True)
            
        print (self._prompt, end="", flush=True)
        
    #========================================================================
    # command input history
    #========================================================================
        
    def _get_history (self, index):
        if ((index >= 0) and (index < len (self._history))):
            self._clear_line()
            self._line = self._history [index]
            print (self._line, end="", flush=True)
            
    #========================================================================
    # The main body of command line input
    # use ctrl-d to switch between uart raw mode (namely, switch between
    # the OCD uart and regular uart)
    #========================================================================
            
    def input (self):
        self._line = ""
        history_index = len (self._history)
        
        if (self.uart_raw_mode_enable == 0):
            print (self._prompt, end="", flush=True)
        
        while(1):
            if (self.uart_raw_mode_enable):
                if self._kbhit():
                    c = self._getch()
                else:
                    c = chr(0)
            else:
                c = self._getch()
            
            if (self.uart_raw_mode_enable):
                if (ord(c) == 0):
                    self._line = ""
                elif (ord(c) == 4): # ctrl-d
                    self._line = "uart_switch"
                else:
                    self._line = c.decode()
                break
                
            if (ord(c) > 127):
                c = self._getch()
                if (ord(c) == ord('H')): # up arrow
                    if (history_index >= 0):
                        history_index = history_index - 1
                    self._get_history(history_index)
                elif (ord(c) == ord('P')): # down arrow    
                    if (history_index < (len(self._history) - 1)):
                        history_index = history_index + 1
                    self._get_history(history_index)
                    
            elif (self._input_valid(ord(c))):
                print (c.decode(), end="", flush=True)
                self._line = self._line + c.decode()
            elif (ord(c) == ord('\r')):
                print ("");
                break
            elif (ord(c) == ord('\t')):
                self._line = self._line + self._tab_completion()
            elif (ord(c) == 8): # backspace
                if (len (self._line)):
                    print ("\b \b", end="", flush=True)
                    self._line = self._line[:-1]
            elif (ord(c) == 4): # ctrl-d
                self._line = "uart_switch"    
                break
            
        if (len(self._line) and (self._line != "uart_switch")):
            if (len(self._history)):
                if (self._history[len(self._history) - 1] == self._line):
                    pass
                elif (self.uart_raw_mode_enable == 0):
                    self._history.append (self._line)
            elif (self.uart_raw_mode_enable == 0):        
                self._history.append (self._line)
        
        return self._line

        
#############################################################################
# Main
#############################################################################
        
def main():

    ocd_stdin = OCD_Input(">> ", ["help", "cpu_reset", "cpu_resume", "cpu_pause"])
    for i in range (5):
        ocd_stdin.input()
    
if __name__ == "__main__":
    main()        

