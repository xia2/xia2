#include <hdf5.h>
#include <stdlib.h>
#include <string.h>

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

int wrap_gcreate(hid_t fid, const char * name)
{
  hid_t gid;

  gid = H5Gcreate(fid, name, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);

  return gid;
}

int add_int_image(hid_t gid, int rank, hsize_t * dim, const char * name,
		  int * data)
{
  hid_t datatype, dataspace, dataprop, dataid;
  hid_t atts, atttype, attid;
  int signal_flag;

  dataspace = H5Screate_simple(rank, dim, dim);
  datatype = H5Tcopy(H5T_NATIVE_INT);  
  dataprop = H5Pcreate(H5P_DATASET_CREATE);
  dataid = H5Dcreate(gid, (char *) "data", datatype, dataspace, H5P_DEFAULT,
		     H5P_DEFAULT, H5P_DEFAULT);
  H5Dwrite(dataid, datatype, H5S_ALL, H5S_ALL, H5P_DEFAULT, data);
  H5Sclose(dataspace);
  H5Tclose(datatype);
  H5Pclose(dataprop);  

  atts = H5Screate(H5S_SCALAR);
  atttype = H5Tcopy(H5T_NATIVE_INT);
  H5Tset_size(atttype, 1);
  attid = H5Acreate(dataid, "signal", atttype, atts, H5P_DEFAULT, H5P_DEFAULT);
  signal_flag = 1;
  H5Awrite(attid, atttype, & signal_flag);
  H5Sclose(atts);
  H5Tclose(atttype);
  H5Aclose(attid);

  H5Dclose(dataid);

  return 0;
}
  
int open_hdf5_file(char * filename)
{
  hid_t fid, fapl;

  fapl = H5Pcreate(H5P_FILE_ACCESS);
  H5Pset_fclose_degree(fapl, H5F_CLOSE_STRONG);
  fid = H5Fcreate(filename, H5F_ACC_TRUNC, H5P_DEFAULT, fapl);  
  H5Pclose(fapl);

  return fid;
}

int close_hdf5_file(hid_t fid)
{
  H5Fclose(fid);
  return 0;
}

int main(int argc, char ** argv)
{
  int * data;
  int i, j, k, rank, nx, ny;
  hid_t fid, gid;
  hsize_t dim[2];

  char data_name[100];

  /* really crappy error trapping */
  if (argc < 2) return 1;

  nx = 100;
  ny = 100;

  data = (int *) malloc (sizeof(int) * nx * ny);

  dim[0] = ny; dim[1] = nx;
  rank = 2;

  fid = open_hdf5_file(argv[1]);

  gid = wrap_gcreate(fid, "profile");
  
  wrap_acreate(gid, "NXentry");

  for (k = 0; k < 100; k ++) {
    for (i = 0; i < ny; i++) {
      for (j = 0; j < nx; j++) {
	data[i * nx + j] = (i + j) % (k + 1);
      }
    }

    sprintf(data_name, "/profile/peak%03d", k);

    gid = wrap_gcreate(fid, data_name);
    
    wrap_acreate(gid, "NXdata");

    sprintf(data_name, "data %03d", k);
    add_int_image(gid, rank, dim, data_name, data);
  }

  close_hdf5_file(fid);

  free(data);

  return 0;
}
