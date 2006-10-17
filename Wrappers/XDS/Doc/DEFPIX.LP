
 ***** DEFPIX *****  (XDS VERSION  June 2006)               17-Oct-2006

 Recognizes untrusted detector pixels in the initial background
 table BKGINIT.pck, previously determined by the program step
 INIT. Untrusted pixels may result from shading parts of the
 detector area by hardware absorbing x-rays emanating from the
 crystal. DEFPIX generates the control image ABS.pck which
 should be inspected with the VIEW program. Unshaded pixels
 have values around 10000, while shaded regions are recognized
 by their lower vales, typically below 7000. Trusted pixels
 must have values within an allowed range as specified by the
 input parameter VALUE_RANGE_FOR_TRUSTED_DETECTOR_PIXELS=
 in XDS.INP. In addition, accepted pixels must be within a
 resolution range, defined in XDS.INP as the parameter
 INCLUDE_RESOLUTION_RANGE=
    Excluded pixels are marked by -3 in the pixel background
 table BKGPIX.pck. This table is required by the subsequent
 INTEGRATE step and should be inspected by the user with the
 VIEW program.

 VALUE_RANGE_FOR_TRUSTED_DETECTOR_PIXELS=             7000.    30000.
 INCLUDE_RESOLUTION_RANGE=                          100.000     1.650
 RESOLUTION RANGE RECORDED BY DETECTOR (ANGSTROM)    99.881     1.650
 NUMBER OF PIXELS REMOVED FROM   "BKGINIT.pck"       452219
 NUMBER OF TRUSTED PIXELS IN      "BKGPIX.pck"      3697150
 MEAN VALUE OF TRUSTED PIXELS IN  "BKGPIX.pck"      151.936


 cpu time used                  2.5 sec
 elapsed wall-clock time        2.5 sec
