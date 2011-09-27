  void
  column::set_values(
    af::const_ref<float> const& values,
    af::const_ref<bool> const& selection_valid) const
  {
    int n_refl = mtz_object().n_reflections();

    // cope with case where we have a new reflection file object with nref
    // set to 0. if so, allocate then use ccp4_lwrefl to assign the values.

    if (n_refl == 0) {

      CMtz::MTZ* p = mtz_object().ptr();
      float const& not_a_number_value = mtz_object().not_a_number_value();

      CMtz::MTZCOL* col_ptrs[1];
      col_ptrs[0] = ptr();

      mtz_object().adjust_column_array_sizes(static_cast<int>(values.size()));
      for (std::size_t i_value = 0; i_value < values.size(); i_value ++) {
	int irefl = p -> nref;
	float value;
	
	if (selection_valid.size() == 0 || selection_valid[i_value]) {
	  value = values[i_value];
	} else {
	  value = not_a_number_value;
	}

	if (!CMtz::ccp4_lwrefl(p, &value, col_ptrs, 1, irefl + 1)) {
          throw cctbx::error(CCP4::ccp4_strerror(ccp4_errno));
        }
      }
      
      return;
    }

    IOTBX_ASSERT(values.size() == static_cast<std::size_t>(n_refl));
    if (selection_valid.size() != 0) {
      IOTBX_ASSERT(selection_valid.size() == static_cast<std::size_t>(n_refl));
    }
    float const& not_a_number_value = mtz_object().not_a_number_value();
    float* ref = ptr()->ref;
    for(int i=0;i<n_refl;i++) {
      if (selection_valid.size() == 0 || selection_valid[i]) {
        ref[i] = values[i];
      }
      else {
        ref[i] = not_a_number_value;
      }
    }
  }

