% Driver.mp
% Maintained by G.Winter
% 16th June 2006
% 
% A UML description of how the Driver class and related beasties
% work, including the factories and the like.
% 
% 

input metauml;

beginfig(1);

  iClass.foreColor := (0.9, 0.9, 0.0);

  Class.SimpleDriver("SimpleDriver")()("Driver():Driver");
  Class.ScriptDriver("ScriptDriver")()("Driver():Driver");
  Class.SunGridEngineDriver("SunGridEngineDriver")()("Driver():Driver");

  Class.Driver("Driver")()("Driver():Driver");
  classStereotypes.Driver("<<interface>>");

  Driver.info.foreColor := (0.9, 0.9, 0.9);

  Class.ClusterDriver("ClusterDriver")()("submit()",
                                         "cleanup()");
  classStereotypes.ClusterDriver("<<interface>>");

  ClusterDriver.info.foreColor := (0.9, 0.9, 0.9);

  Class.DriverFactory("DriverFactory")()("Driver():Driver");
  classStereotypes.DriverFactory("<<factory>>");

  DriverFactory.info.foreColor := (0.9, 0.45, 0.45);  

  Class.ClusterDriverFactory("ClusterDriverFactory")()("Driver():Driver");
  classStereotypes.ClusterDriverFactory("<<factory>>");

  ClusterDriverFactory.info.foreColor := (0.9, 0.45, 0.45);  

  Note.Help("Applications wanting",
            "a Driver instance should",
            "use DriverFactory.Driver()");

  SimpleDriver.midy = ScriptDriver.midy = ClusterDriverFactory.midy;

  Driver.top = ScriptDriver.bottom - 40;
  ClusterDriver.midx = Driver.midx;
  ClusterDriver.bottom = ScriptDriver.top + 40;
  DriverFactory.midy = Driver.midy;
  Driver.midx = SimpleDriver.midx;
  SunGridEngineDriver.midx = ClusterDriverFactory.midx;
  SunGridEngineDriver.bottom = ClusterDriverFactory.top + 40;
  DriverFactory.midx = ClusterDriverFactory.midx;

  ScriptDriver.left = SimpleDriver.right + 20;
  ClusterDriverFactory.left = ScriptDriver.right + 20;

  Help.left = DriverFactory.right + 40;
  Help.top = DriverFactory.top;

  drawObject(SimpleDriver);
  drawObject(ScriptDriver);
  drawObject(ClusterDriver);
  drawObject(ClusterDriverFactory);
  drawObject(SunGridEngineDriver);
  drawObject(Driver);
  drawObject(DriverFactory);
  drawObject(Help);

  link(inheritance)(SimpleDriver.s -- Driver.n);  
  link(inheritance)(ScriptDriver.s -- Driver.n);  
  link(inheritance)(ClusterDriver.sw -- Driver.n);  

  link(inheritance)(SunGridEngineDriver.w -- ClusterDriver.e);

  link(aggregationUni)(Driver.e -- DriverFactory.w);
  link(aggregationUni)(ClusterDriver.e -- ClusterDriverFactory.w);
  link(associationUni)(SunGridEngineDriver.s -- ClusterDriverFactory.n);
  
  link(associationUni)(SimpleDriver.s -- DriverFactory.n);  
  link(associationUni)(ScriptDriver.s -- DriverFactory.n);  
  link(associationUni)(ClusterDriverFactory.s -- DriverFactory.n);  

  clink(dashedLink)(DriverFactory.methodStack.pict[0],
                    Help);

endfig;
end