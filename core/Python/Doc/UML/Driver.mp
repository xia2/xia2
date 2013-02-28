% Driver.mp
% 
% A metapost description of the interface the Driver class in xia2core.
% This relies on the MetaUML package available on sourceforge.net.
% 
% Maintained by G.Winter
% 14th June 2006
% 

input metauml;

beginfig(1);
  Interface.D("Driver")
    ("+setExecutable(executable:string)",
     "+getExecutable():string",
     "+setTask(task:string)",
     "+getTask():string",
     "+addInput_file(input:file)",
     "+addOutput_file(output:file)",
     "+addCommand_line(token:string)",
     "+setWorking_directory(directory:directory)",
     "+getWorking_directory():directory",
     "+start()",
     "+check()",
     "+check_for_errors()",
     "+input(record:string)",
     "+output():string",
     "+finished():boolean",
     "+get_all_output():string[]",
     "+close()",
     "+close_wait()",
     "+kill()",
     "+status()");

  drawObject(D);
endfig;
end