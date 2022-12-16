#include <stdio.h>
#include "hocdec.h"
extern int nrnmpi_myid;
extern int nrn_nobanner_;

extern "C" void _ampa_reg(void);
extern "C" void _CaDynamics_E2_reg(void);
extern "C" void _CaDynamics_E2_v2_reg(void);
extern "C" void _Ca_HVA_reg(void);
extern "C" void _Ca_LVAst_reg(void);
extern "C" void _epsp_reg(void);
extern "C" void _gsyn_reg(void);
extern "C" void _Ih_reg(void);
extern "C" void _Im_reg(void);
extern "C" void _k2syn_reg(void);
extern "C" void _K_Pst_reg(void);
extern "C" void _K_Tst_reg(void);
extern "C" void _Nap_Et2_reg(void);
extern "C" void _NaTa_t_reg(void);
extern "C" void _NaTg_reg(void);
extern "C" void _NaTs2_t_reg(void);
extern "C" void _netgaba_reg(void);
extern "C" void _netglutamate_reg(void);
extern "C" void _nmda2_reg(void);
extern "C" void _nmda2_schiller_reg(void);
extern "C" void _SK_E2_reg(void);
extern "C" void _SKv3_1_copy_reg(void);
extern "C" void _SKv3_1_reg(void);
extern "C" void _vecevent_reg(void);

extern "C" void modl_reg() {
  if (!nrn_nobanner_) if (nrnmpi_myid < 1) {
    fprintf(stderr, "Additional mechanisms from files\n");
    fprintf(stderr, " \"ampa.mod\"");
    fprintf(stderr, " \"CaDynamics_E2.mod\"");
    fprintf(stderr, " \"CaDynamics_E2_v2.mod\"");
    fprintf(stderr, " \"Ca_HVA.mod\"");
    fprintf(stderr, " \"Ca_LVAst.mod\"");
    fprintf(stderr, " \"epsp.mod\"");
    fprintf(stderr, " \"gsyn.mod\"");
    fprintf(stderr, " \"Ih.mod\"");
    fprintf(stderr, " \"Im.mod\"");
    fprintf(stderr, " \"k2syn.mod\"");
    fprintf(stderr, " \"K_Pst.mod\"");
    fprintf(stderr, " \"K_Tst.mod\"");
    fprintf(stderr, " \"Nap_Et2.mod\"");
    fprintf(stderr, " \"NaTa_t.mod\"");
    fprintf(stderr, " \"NaTg.mod\"");
    fprintf(stderr, " \"NaTs2_t.mod\"");
    fprintf(stderr, " \"netgaba.mod\"");
    fprintf(stderr, " \"netglutamate.mod\"");
    fprintf(stderr, " \"nmda2.mod\"");
    fprintf(stderr, " \"nmda2_schiller.mod\"");
    fprintf(stderr, " \"SK_E2.mod\"");
    fprintf(stderr, " \"SKv3_1_copy.mod\"");
    fprintf(stderr, " \"SKv3_1.mod\"");
    fprintf(stderr, " \"vecevent.mod\"");
    fprintf(stderr, "\n");
  }
  _ampa_reg();
  _CaDynamics_E2_reg();
  _CaDynamics_E2_v2_reg();
  _Ca_HVA_reg();
  _Ca_LVAst_reg();
  _epsp_reg();
  _gsyn_reg();
  _Ih_reg();
  _Im_reg();
  _k2syn_reg();
  _K_Pst_reg();
  _K_Tst_reg();
  _Nap_Et2_reg();
  _NaTa_t_reg();
  _NaTg_reg();
  _NaTs2_t_reg();
  _netgaba_reg();
  _netglutamate_reg();
  _nmda2_reg();
  _nmda2_schiller_reg();
  _SK_E2_reg();
  _SKv3_1_copy_reg();
  _SKv3_1_reg();
  _vecevent_reg();
}
