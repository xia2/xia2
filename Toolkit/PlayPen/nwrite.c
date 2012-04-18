#include <hdf5.h>
#include <stdlib.h>
#include <string.h>

#define NX 100
#define NY 100

int wrap_acreate(hid_t gid, const char * attribute_name)
{
  hid_t atts, atttype, attid;

  atts = H5Screate(H5S_SCALAR);
  atttype = H5Tcopy(H5T_C_S1);
  H5Tset_size(atttype, strlen(attribute_name));
  attid = H5Acreate(gid, "NX_class", atttype, atts, H5P_DEFAULT, H5P_DEFAULT);
  H5Awrite(attid, atttype, (char *) attribute_name);
  H5Sclose(atts);
  H5Tclose(atttype);
  H5Aclose(attid);
  return 0;
}
  
int main(int argc, char *argv[])
{
  int data[NY][NX];
  int i, j, rank, signal;

  hid_t fid, fapl, gid, atts, atttype, attid;
  hid_t datatype, dataspace, dataprop, dataid;
  hsize_t dim[2];

  /* really crappy error trapping */
  if (argc < 2) return 1;

  for (i = 0; i < NY; i++) {
    for (j = 0; j < NX; j++) {
      data[i][j] = i + j;
    }
  }

  dim[0] = NY; dim[1] = NX;
  rank = 2;

  fapl = H5Pcreate(H5P_FILE_ACCESS);
  H5Pset_fclose_degree(fapl, H5F_CLOSE_STRONG);
  fid = H5Fcreate(argv[1], H5F_ACC_TRUNC, H5P_DEFAULT, fapl);  
  H5Pclose(fapl);

  gid = H5Gcreate(fid, (const char *)"scan", H5P_DEFAULT, H5P_DEFAULT, 
		  H5P_DEFAULT);
  
  wrap_acreate(gid, "NXEntry");

  gid = H5Gcreate(fid, (const char *)"/scan/data", H5P_DEFAULT, 
		  H5P_DEFAULT, H5P_DEFAULT);

  wrap_acreate(gid, "NXdata");

  dataspace = H5Screate_simple(rank, dim, dim);
  datatype = H5Tcopy(H5T_NATIVE_INT);  
  dataprop = H5Pcreate(H5P_DATASET_CREATE);
  dataid = H5Dcreate(gid, (char *) "data", datatype, dataspace, H5P_DEFAULT,
		     H5P_DEFAULT, H5P_DEFAULT);
  H5Dwrite(dataid, datatype, H5S_ALL, H5S_ALL, H5P_DEFAULT, data);
  H5Sclose(dataspace);
  H5Tclose(datatype);
  H5Pclose(dataprop);  

  /*
   * set the signal=1 attribute - no idea what this does!
   */
  atts = H5Screate(H5S_SCALAR);
  atttype = H5Tcopy(H5T_NATIVE_INT);
  H5Tset_size(atttype,1);
  attid = H5Acreate(dataid, "signal", atttype, atts, H5P_DEFAULT, H5P_DEFAULT);
  signal = 1;
  H5Awrite(attid, atttype, &signal);
  H5Sclose(atts);
  H5Tclose(atttype);
  H5Aclose(attid);

  H5Dclose(dataid);

  H5Fclose(fid);

  return 0;
}
