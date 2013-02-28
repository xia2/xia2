% DriverInterface.mp
% Maintained by G.Winter
% 19th June 2006
% 
% A description of the Driver interface - and how it may be used.
% 

input metauml;

beginfig(1);

  Class.Driver("Driver")()("setExecutable(string)",
                           "getExecutable():string",
                           "setTask(string)",
                           "getTask():string",
                           "addCommand_line(string)",
                           "+start()",
                           "+close()",
                           "+close_wait()",
                           "+kill()",
                           "write_log_file(string)",
                           "+status()",
                           "+input(string)",
                           "+output():string",
                           "+finished():boolean",
                           "get_all_output():string[]");

  classStereotypes.Driver("<<interface>>");
  Driver.info.foreColor := (0.9, 0.9, 0.9);

  drawObject(Driver);
endfig;
end
