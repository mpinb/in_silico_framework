#include <cstdio>
namespace coreneuron {
extern int nrnmpi_myid;
extern int nrn_nobanner_;
extern int _CaDynamics_E2_reg(void),
  _CaDynamics_E2_v2_reg(void),
  _Ca_HVA_reg(void),
  _Ca_LVAst_reg(void),
  _Ih_reg(void),
  _Im_reg(void),
  _K_Pst_reg(void),
  _K_Tst_reg(void),
  _NaTa_t_reg(void),
  _NaTg_reg(void),
  _NaTs2_t_reg(void),
  _Nap_Et2_reg(void),
  _SK_E2_reg(void),
  _SKv3_1_reg(void),
  _SKv3_1_copy_reg(void),
  _ampa_reg(void),
  _epsp_reg(void),
  _exp2syn_reg(void),
  _expsyn_reg(void),
  _gsyn_reg(void),
  _hh_reg(void),
  _k2syn_reg(void),
  _netgaba_reg(void),
  _netglutamate_reg(void),
  _netstim_reg(void),
  _nmda2_reg(void),
  _nmda2_schiller_reg(void),
  _passive_reg(void),
  _pattern_reg(void),
  _stim_reg(void),
  _svclmp_reg(void),
  _vecevent_reg(void);

void modl_reg() {
    if (!nrn_nobanner_ && nrnmpi_myid < 1) {
        fprintf(stderr, " Additional mechanisms from files\n");
        fprintf(stderr, " CaDynamics_E2.mod");
        fprintf(stderr, " CaDynamics_E2_v2.mod");
        fprintf(stderr, " Ca_HVA.mod");
        fprintf(stderr, " Ca_LVAst.mod");
        fprintf(stderr, " Ih.mod");
        fprintf(stderr, " Im.mod");
        fprintf(stderr, " K_Pst.mod");
        fprintf(stderr, " K_Tst.mod");
        fprintf(stderr, " NaTa_t.mod");
        fprintf(stderr, " NaTg.mod");
        fprintf(stderr, " NaTs2_t.mod");
        fprintf(stderr, " Nap_Et2.mod");
        fprintf(stderr, " SK_E2.mod");
        fprintf(stderr, " SKv3_1.mod");
        fprintf(stderr, " SKv3_1_copy.mod");
        fprintf(stderr, " ampa.mod");
        fprintf(stderr, " epsp.mod");
        fprintf(stderr, " exp2syn.mod");
        fprintf(stderr, " expsyn.mod");
        fprintf(stderr, " gsyn.mod");
        fprintf(stderr, " hh.mod");
        fprintf(stderr, " k2syn.mod");
        fprintf(stderr, " netgaba.mod");
        fprintf(stderr, " netglutamate.mod");
        fprintf(stderr, " netstim.mod");
        fprintf(stderr, " nmda2.mod");
        fprintf(stderr, " nmda2_schiller.mod");
        fprintf(stderr, " passive.mod");
        fprintf(stderr, " pattern.mod");
        fprintf(stderr, " stim.mod");
        fprintf(stderr, " svclmp.mod");
        fprintf(stderr, " vecevent.mod");
        fprintf(stderr, "\n\n");
    }

    _CaDynamics_E2_reg();
    _CaDynamics_E2_v2_reg();
    _Ca_HVA_reg();
    _Ca_LVAst_reg();
    _Ih_reg();
    _Im_reg();
    _K_Pst_reg();
    _K_Tst_reg();
    _NaTa_t_reg();
    _NaTg_reg();
    _NaTs2_t_reg();
    _Nap_Et2_reg();
    _SK_E2_reg();
    _SKv3_1_reg();
    _SKv3_1_copy_reg();
    _ampa_reg();
    _epsp_reg();
    _exp2syn_reg();
    _expsyn_reg();
    _gsyn_reg();
    _hh_reg();
    _k2syn_reg();
    _netgaba_reg();
    _netglutamate_reg();
    _netstim_reg();
    _nmda2_reg();
    _nmda2_schiller_reg();
    _passive_reg();
    _pattern_reg();
    _stim_reg();
    _svclmp_reg();
    _vecevent_reg();
}
} //namespace coreneuron
