% Decorator.mp
% Maintained by G.Winter
% 16th June 2006
% 
% A UML description of the relationships between Driver instances, the 
% DriverFactory, Decorators and the DecoratorFactory.
% 

input metauml;

beginfig(1);

  iClass.foreColor := (0.9, 0.9, 0.0);

  Class.Driver("Driver")()("Driver():Driver");
  classStereotypes.Driver("<<interface>>");

  Driver.info.foreColor := (0.9, 0.9, 0.9);

  Class.CCPDriver("CCP4 Driver")()(); 

  Note.Help("No constructor -",
            "only available",
            "through factory");

  Class.DecoratorFactory("DecoratorFactory")
                        ()
                        ("Decorate(driverInstance, type)");

  classStereotypes.DecoratorFactory("<<factory>>");

  DecoratorFactory.info.foreColor := (0.9, 0.45, 0.45);

  Driver.midx = CCPDriver.midx;
  CCPDriver.top = Driver.bottom - 40;

  DecoratorFactory.midy = Driver.midy;
  DecoratorFactory.left = Driver.right + 20;
  
  Help.midy = CCPDriver.midy;
  Help.left = CCPDriver.right + 20;

  drawObject(Driver);
  drawObject(CCPDriver);
  drawObject(Help);
  drawObject(DecoratorFactory);

  link(inheritance)(CCPDriver.n -- Driver.s);
  link(aggregationUni)(CCPDriver.e -- DecoratorFactory.s);
  clink(dashedLink)(CCPDriver.methodStack, Help);

endfig;
end
