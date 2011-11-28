/* gsimII kernel tcl interface v1.0
 * maintained by g.winter
 * 15th august 2000
 * 
 * Copyright (c) 1988-1994 The Regents of the University of California.
 * Copyright (c) 1994-1996 Sun Microsystems, Inc.
 *
 */

#include "tcl.h"
#include "mpsa_export.h"

extern int Tcl_LinkVar();
int (*tclDummyLinkVarPtr)() = Tcl_LinkVar;
extern int isatty _ANSI_ARGS_((int));
extern char *strcpy _ANSI_ARGS_((char *, const char *));
static Tcl_Interp *interp;
static Tcl_DString command;

/*
 * Tcl Main program lifted direct.
 */

void mpsa_TclMain(
  int argc,
  char **argv,
  Tcl_AppInitProc *appInitProc
)
{
  char buffer[1000], *cmd, *args, *fileName;
  int code, gotPartial, tty, length;
  int exitCode = 0;
  Tcl_Channel inChannel, outChannel, errChannel;
  Tcl_DString temp;
  Tcl_Interp *interp;
  
  Tcl_FindExecutable(argv[0]);
  interp = Tcl_CreateInterp();

  /* 
   * get command line arguments so that script may be started
   * or command line arguments used.
   */

  fileName = NULL;
  if ((argc > 1) && (argv[1][0] != '-')) {
    fileName = argv[1];
    argc--;
    argv++;
  }
  args = Tcl_Merge(argc-1, argv+1);
  Tcl_SetVar(interp, "argv", args, TCL_GLOBAL_ONLY);
  ckfree(args);
  sprintf(buffer, "%d", argc-1);
  Tcl_SetVar(interp, "argc", buffer, TCL_GLOBAL_ONLY);
  Tcl_SetVar(interp, "argv0", (fileName != NULL) ? fileName : argv[0],
    TCL_GLOBAL_ONLY);
  
  /*
   * Set the "tcl_interactive" variable.
   */
  
  tty = isatty(0);
  Tcl_SetVar(interp, "tcl_interactive",
    ((fileName == NULL) && tty) ? "1" : "0", TCL_GLOBAL_ONLY);
  
  /*
   * Invoke application-specific initialization.
   */
  
  if ((*appInitProc)(interp) != TCL_OK) {
    errChannel = Tcl_GetStdChannel(TCL_STDERR);
    if (errChannel) {
      Tcl_Write(errChannel,
        "application-specific initialization failed: ", -1);
      Tcl_Write(errChannel, interp->result, -1);
      Tcl_Write(errChannel, "\n", 1);
    }
  }
  
  /*
   * If a script file was specified then just source that file
   * and quit.
   */
  
  if (fileName != NULL) {
    code = Tcl_EvalFile(interp, fileName);
    if (code != TCL_OK) {
      errChannel = Tcl_GetStdChannel(TCL_STDERR);
      if (errChannel) {
	/*
	 * The following statement guarantees that the errorInfo
	 * variable is set properly.
	 */
	
	Tcl_AddErrorInfo(interp, "");
	Tcl_Write(errChannel,
	  Tcl_GetVar(interp, "errorInfo", TCL_GLOBAL_ONLY), -1);
	Tcl_Write(errChannel, "\n", 1);
      }
      exitCode = 1;
    }
    goto done;
  }

  /*
   * We're running interactively.  Source a user-specific startup
   * file if the application specified one and if the file exists.
   */
  
  fileName = Tcl_GetVar(interp, "tcl_rcFileName", TCL_GLOBAL_ONLY);

  if (fileName != NULL) {
    Tcl_Channel c;
    char *fullName;
    
    Tcl_DStringInit(&temp);
    fullName = Tcl_TranslateFileName(interp, fileName, &temp);
    if (fullName == NULL) {
      errChannel = Tcl_GetStdChannel(TCL_STDERR);
      if (errChannel) {
	Tcl_Write(errChannel, interp->result, -1);
	Tcl_Write(errChannel, "\n", 1);
      }
    } else {
      
      /*
       * Test for the existence of the rc file before trying to read it.
       */
      
      c = Tcl_OpenFileChannel(NULL, fullName, "r", 0);
      if (c != (Tcl_Channel) NULL) {
	Tcl_Close(NULL, c);
	if (Tcl_EvalFile(interp, fullName) != TCL_OK) {
	  errChannel = Tcl_GetStdChannel(TCL_STDERR);
	  if (errChannel) {
	    Tcl_Write(errChannel, interp->result, -1);
	    Tcl_Write(errChannel, "\n", 1);
	  }
	}
      }
    }
    Tcl_DStringFree(&temp);
  }

  /*
   * Process commands from stdin until there's an end-of-file.  Note
   * that we need to fetch the standard channels again after every
   * eval, since they may have been changed.
   */

  gotPartial = 0;
  Tcl_DStringInit(&command);
  inChannel = Tcl_GetStdChannel(TCL_STDIN);
  outChannel = Tcl_GetStdChannel(TCL_STDOUT);
  while (1) {
    if (tty) {
      char *promptCmd;
      promptCmd = Tcl_GetVar(interp,
        gotPartial ? "tcl_prompt2" : "tcl_prompt1", TCL_GLOBAL_ONLY);
      if (promptCmd == NULL) {
      defaultPrompt:
	if (!gotPartial && outChannel) {
	  Tcl_Write(outChannel, "mpsa> ", 6);
	}
      } else {
	code = Tcl_Eval(interp, promptCmd);
	inChannel = Tcl_GetStdChannel(TCL_STDIN);
	outChannel = Tcl_GetStdChannel(TCL_STDOUT);
	errChannel = Tcl_GetStdChannel(TCL_STDERR);
	if (code != TCL_OK) {
	  if (errChannel) {
	    Tcl_Write(errChannel, interp->result, -1);
	    Tcl_Write(errChannel, "\n", 1);
	  }
	  Tcl_AddErrorInfo(interp,
	    "\n    (script that generates prompt)");
	  goto defaultPrompt;
	}
      }
      if (outChannel) {
	Tcl_Flush(outChannel);
      }
    }
    if (!inChannel) {
      goto done;
    }
    
    length = Tcl_Gets(inChannel, &command);
    
    if (length < 0) {
      goto done;
    }
    if ((length == 0) && Tcl_Eof(inChannel) && (!gotPartial)) {
      goto done;
    }
    
    /*
     * Add the newline removed by Tcl_Gets back to the string.
     */
    
    (void) Tcl_DStringAppend(&command, "\n", -1);
    
    cmd = Tcl_DStringValue(&command);
    if (!Tcl_CommandComplete(cmd)) {
      gotPartial = 1;
      continue;
    }

    gotPartial = 0;
    code = Tcl_RecordAndEval(interp, cmd, 0);
    inChannel = Tcl_GetStdChannel(TCL_STDIN);
    outChannel = Tcl_GetStdChannel(TCL_STDOUT);
    errChannel = Tcl_GetStdChannel(TCL_STDERR);
    Tcl_DStringFree(&command);
    if (code != TCL_OK) {
      if (errChannel) {
	Tcl_Write(errChannel, interp->result, -1);
	Tcl_Write(errChannel, "\n", 1);
      }
    } else if (tty && (*interp->result != 0)) {
      if (outChannel) {
	Tcl_Write(outChannel, interp->result, -1);
	Tcl_Write(outChannel, "\n", 1);
      }
    }
  }
done:
  sprintf(buffer, "exit %d", exitCode);
  Tcl_Eval(interp, buffer);
}
