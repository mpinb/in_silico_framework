/* Created by Language version: 7.7.0 */
/* VECTORIZED */
#define NRN_VECTORIZED 1
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "mech_api.h"
#undef PI
#define nil 0
#define _pval pval
#include "md1redef.h"
#include "section.h"
#include "nrniv_mf.h"
#include "md2redef.h"
 
#if !NRNGPU
#undef exp
#define exp hoc_Exp
#endif
 
#define nrn_init _nrn_init__glutamate_syn
#define _nrn_initial _nrn_initial__glutamate_syn
#define nrn_cur _nrn_cur__glutamate_syn
#define _nrn_current _nrn_current__glutamate_syn
#define nrn_jacob _nrn_jacob__glutamate_syn
#define nrn_state _nrn_state__glutamate_syn
#define _net_receive _net_receive__glutamate_syn 
#define state state__glutamate_syn 
 
#define _threadargscomma_ _p, _ppvar, _thread, _nt,
#define _threadargsprotocomma_ double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt,
#define _threadargs_ _p, _ppvar, _thread, _nt
#define _threadargsproto_ double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt
 	/*SUPPRESS 761*/
	/*SUPPRESS 762*/
	/*SUPPRESS 763*/
	/*SUPPRESS 765*/
	 extern double *hoc_getarg(int);
 /* Thread safe. No static _p or _ppvar. */
 
#define t _nt->_t
#define dt _nt->_dt
#define gnmdamax _p[0]
#define gnmdamax_columnindex 0
#define gampamax _p[1]
#define gampamax_columnindex 1
#define e _p[2]
#define e_columnindex 2
#define tau1 _p[3]
#define tau1_columnindex 3
#define tau2 _p[4]
#define tau2_columnindex 4
#define tau3 _p[5]
#define tau3_columnindex 5
#define tau4 _p[6]
#define tau4_columnindex 6
#define decayampa _p[7]
#define decayampa_columnindex 7
#define decaynmda _p[8]
#define decaynmda_columnindex 8
#define taudampa _p[9]
#define taudampa_columnindex 9
#define taudnmda _p[10]
#define taudnmda_columnindex 10
#define taufampa _p[11]
#define taufampa_columnindex 11
#define facilampa _p[12]
#define facilampa_columnindex 12
#define taufnmda _p[13]
#define taufnmda_columnindex 13
#define facilnmda _p[14]
#define facilnmda_columnindex 14
#define inmda _p[15]
#define inmda_columnindex 15
#define iampa _p[16]
#define iampa_columnindex 16
#define gnmda _p[17]
#define gnmda_columnindex 17
#define gampa _p[18]
#define gampa_columnindex 18
#define A _p[19]
#define A_columnindex 19
#define B _p[20]
#define B_columnindex 20
#define C _p[21]
#define C_columnindex 21
#define D _p[22]
#define D_columnindex 22
#define dampa _p[23]
#define dampa_columnindex 23
#define dnmda _p[24]
#define dnmda_columnindex 24
#define fampa _p[25]
#define fampa_columnindex 25
#define fnmda _p[26]
#define fnmda_columnindex 26
#define factor1 _p[27]
#define factor1_columnindex 27
#define factor2 _p[28]
#define factor2_columnindex 28
#define DA _p[29]
#define DA_columnindex 29
#define DB _p[30]
#define DB_columnindex 30
#define DC _p[31]
#define DC_columnindex 31
#define DD _p[32]
#define DD_columnindex 32
#define Ddampa _p[33]
#define Ddampa_columnindex 33
#define Ddnmda _p[34]
#define Ddnmda_columnindex 34
#define Dfampa _p[35]
#define Dfampa_columnindex 35
#define Dfnmda _p[36]
#define Dfnmda_columnindex 36
#define v _p[37]
#define v_columnindex 37
#define _g _p[38]
#define _g_columnindex 38
#define _tsav _p[39]
#define _tsav_columnindex 39
#define _nd_area  *_ppvar[0].get<double*>()
 
#if MAC
#if !defined(v)
#define v _mlhv
#endif
#if !defined(h)
#define h _mlhh
#endif
#endif
 static int hoc_nrnpointerindex =  -1;
 static Datum* _extcall_thread;
 static Prop* _extcall_prop;
 /* external NEURON variables */
 /* declaration of user functions */
 static int _mechtype;
extern void _nrn_cacheloop_reg(int, int);
extern void hoc_register_prop_size(int, int, int);
extern void hoc_register_limits(int, HocParmLimits*);
extern void hoc_register_units(int, HocParmUnits*);
extern void nrn_promote(Prop*, int, int);
extern Memb_func* memb_func;
 
#define NMODL_TEXT 1
#if NMODL_TEXT
static void register_nmodl_text_and_filename(int mechtype);
#endif
 extern Prop* nrn_point_prop_;
 static int _pointtype;
 static void* _hoc_create_pnt(Object* _ho) { void* create_point_process(int, Object*);
 return create_point_process(_pointtype, _ho);
}
 static void _hoc_destroy_pnt(void*);
 static double _hoc_loc_pnt(void* _vptr) {double loc_point_process(int, void*);
 return loc_point_process(_pointtype, _vptr);
}
 static double _hoc_has_loc(void* _vptr) {double has_loc_point(void*);
 return has_loc_point(_vptr);
}
 static double _hoc_get_loc_pnt(void* _vptr) {
 double get_loc_point_process(void*); return (get_loc_point_process(_vptr));
}
 extern void _nrn_setdata_reg(int, void(*)(Prop*));
 static void _setdata(Prop* _prop) {
 _extcall_prop = _prop;
 }
 static void _hoc_setdata(void* _vptr) { Prop* _prop;
 _prop = ((Point_process*)_vptr)->_prop;
   _setdata(_prop);
 }
 /* connect user functions to hoc names */
 static VoidFunc hoc_intfunc[] = {
 {0, 0}
};
 static Member_func _member_func[] = {
 {"loc", _hoc_loc_pnt},
 {"has_loc", _hoc_has_loc},
 {"get_loc", _hoc_get_loc_pnt},
 {0, 0}
};
 /* declare global and static user variables */
#define gama gama_glutamate_syn
 double gama = 0.08;
#define n n_glutamate_syn
 double n = 0.25;
#define tau_ampa tau_ampa_glutamate_syn
 double tau_ampa = 2;
 /* some parameters have upper and lower limits */
 static HocParmLimits _hoc_parm_limits[] = {
 {0, 0, 0}
};
 static HocParmUnits _hoc_parm_units[] = {
 {"tau_ampa_glutamate_syn", "ms"},
 {"n_glutamate_syn", "/mM"},
 {"gama_glutamate_syn", "/mV"},
 {"gnmdamax", "nS"},
 {"gampamax", "nS"},
 {"e", "mV"},
 {"tau1", "ms"},
 {"tau2", "ms"},
 {"tau3", "ms"},
 {"tau4", "ms"},
 {"taudampa", "ms"},
 {"taudnmda", "ms"},
 {"taufampa", "ms"},
 {"taufnmda", "ms"},
 {"A", "nS"},
 {"B", "nS"},
 {"C", "nS"},
 {"D", "nS"},
 {"inmda", "nA"},
 {"iampa", "nA"},
 {"gnmda", "nS"},
 {"gampa", "nS"},
 {0, 0}
};
 static double A0 = 0;
 static double B0 = 0;
 static double C0 = 0;
 static double D0 = 0;
 static double delta_t = 0.01;
 static double dnmda0 = 0;
 static double dampa0 = 0;
 static double fnmda0 = 0;
 static double fampa0 = 0;
 /* connect global user variables to hoc */
 static DoubScal hoc_scdoub[] = {
 {"tau_ampa_glutamate_syn", &tau_ampa_glutamate_syn},
 {"n_glutamate_syn", &n_glutamate_syn},
 {"gama_glutamate_syn", &gama_glutamate_syn},
 {0, 0}
};
 static DoubVec hoc_vdoub[] = {
 {0, 0, 0}
};
 static double _sav_indep;
 static void nrn_alloc(Prop*);
static void  nrn_init(NrnThread*, Memb_list*, int);
static void nrn_state(NrnThread*, Memb_list*, int);
 static void nrn_cur(NrnThread*, Memb_list*, int);
static void  nrn_jacob(NrnThread*, Memb_list*, int);
 static void _hoc_destroy_pnt(void* _vptr) {
   destroy_point_process(_vptr);
}
 
static int _ode_count(int);
static void _ode_map(int, double**, double**, double*, Datum*, double*, int);
static void _ode_spec(NrnThread*, Memb_list*, int);
static void _ode_matsol(NrnThread*, Memb_list*, int);
 
#define _cvode_ieq _ppvar[2].literal_value<int>()
 static void _ode_matsol_instance1(_threadargsproto_);
 /* connect range variables in _p that hoc is supposed to know about */
 static const char *_mechanism[] = {
 "7.7.0",
"glutamate_syn",
 "gnmdamax",
 "gampamax",
 "e",
 "tau1",
 "tau2",
 "tau3",
 "tau4",
 "decayampa",
 "decaynmda",
 "taudampa",
 "taudnmda",
 "taufampa",
 "facilampa",
 "taufnmda",
 "facilnmda",
 0,
 "inmda",
 "iampa",
 "gnmda",
 "gampa",
 0,
 "A",
 "B",
 "C",
 "D",
 "dampa",
 "dnmda",
 "fampa",
 "fnmda",
 0,
 0};
 
extern Prop* need_memb(Symbol*);

static void nrn_alloc(Prop* _prop) {
	Prop *prop_ion;
	double *_p; Datum *_ppvar;
  if (nrn_point_prop_) {
	_prop->_alloc_seq = nrn_point_prop_->_alloc_seq;
	_p = nrn_point_prop_->param;
	_ppvar = nrn_point_prop_->dparam;
 }else{
 	_p = nrn_prop_data_alloc(_mechtype, 40, _prop);
 	/*initialize range parameters*/
 	gnmdamax = 1;
 	gampamax = 1;
 	e = 0;
 	tau1 = 50;
 	tau2 = 2;
 	tau3 = 2;
 	tau4 = 0.1;
 	decayampa = 0.5;
 	decaynmda = 0.5;
 	taudampa = 200;
 	taudnmda = 200;
 	taufampa = 200;
 	facilampa = 0;
 	taufnmda = 200;
 	facilnmda = 0;
  }
 	_prop->param = _p;
 	_prop->param_size = 40;
  if (!nrn_point_prop_) {
 	_ppvar = nrn_prop_datum_alloc(_mechtype, 3, _prop);
  }
 	_prop->dparam = _ppvar;
 	/*connect ionic variables to this model*/
 
}
 static void _initlists();
  /* some states have an absolute tolerance */
 static Symbol** _atollist;
 static HocStateTolerance _hoc_state_tol[] = {
 {0, 0}
};
 static void _net_receive(Point_process*, double*, double);
 static void _net_init(Point_process*, double*, double);
 extern Symbol* hoc_lookup(const char*);
extern void _nrn_thread_reg(int, int, void(*)(Datum*));
extern void _nrn_thread_table_reg(int, void(*)(double*, Datum*, Datum*, NrnThread*, int));
extern void hoc_register_tolerance(int, HocStateTolerance*, Symbol***);
extern void _cvode_abstol( Symbol**, double*, int);

 extern "C" void _netglutamate_reg() {
	int _vectorized = 1;
  _initlists();
 	_pointtype = point_register_mech(_mechanism,
	 nrn_alloc,nrn_cur, nrn_jacob, nrn_state, nrn_init,
	 hoc_nrnpointerindex, 1,
	 _hoc_create_pnt, _hoc_destroy_pnt, _member_func);
 _mechtype = nrn_get_mechtype(_mechanism[1]);
     _nrn_setdata_reg(_mechtype, _setdata);
 #if NMODL_TEXT
  register_nmodl_text_and_filename(_mechtype);
#endif
  hoc_register_prop_size(_mechtype, 40, 3);
  hoc_register_dparam_semantics(_mechtype, 0, "area");
  hoc_register_dparam_semantics(_mechtype, 1, "pntproc");
  hoc_register_dparam_semantics(_mechtype, 2, "cvodeieq");
 	hoc_register_cvode(_mechtype, _ode_count, _ode_map, _ode_spec, _ode_matsol);
 	hoc_register_tolerance(_mechtype, _hoc_state_tol, &_atollist);
 pnt_receive[_mechtype] = _net_receive;
 pnt_receive_init[_mechtype] = _net_init;
 pnt_receive_size[_mechtype] = 2;
 	hoc_register_var(hoc_scdoub, hoc_vdoub, hoc_intfunc);
 	ivoc_help("help ?1 glutamate_syn /gpfs/soma_fs/scratch/saka/project_src/in_silico_framework/mechanisms/channels_py3_wip/netglutamate.mod\n");
 hoc_register_limits(_mechtype, _hoc_parm_limits);
 hoc_register_units(_mechtype, _hoc_parm_units);
 }
static int _reset;
static const char *modelname = "NMDA synapse with depression";

static int error;
static int _ninits = 0;
static int _match_recurse=1;
static void _modl_cleanup(){ _match_recurse=1;}
 
static int _ode_spec1(_threadargsproto_);
/*static int _ode_matsol1(_threadargsproto_);*/
 static int _slist1[8], _dlist1[8];
 static int state(_threadargsproto_);
 
static void _net_receive (Point_process* _pnt, double* _args, double _lflag) 
{  double* _p; Datum* _ppvar; Datum* _thread; NrnThread* _nt;
   _thread = (Datum*)0; _nt = (NrnThread*)_pnt->_vnt;   _p = _pnt->_prop->param; _ppvar = _pnt->_prop->dparam;
  if (_tsav > t){ hoc_execerror(hoc_object_name(_pnt->ob), ":Event arrived out of order. Must call ParallelContext.set_maxstep AFTER assigning minimum NetCon.delay");}
 _tsav = t; {
   gampamax = _args[0] ;
   gnmdamax = _args[1] ;
     if (nrn_netrec_state_adjust && !cvode_active_){
    /* discon state adjustment for cnexp case (rate uses no local variable) */
    double __state = A;
    double __primary = (A + factor1 * gnmdamax * dnmda * fnmda) - __state;
     __primary += ( 1. - exp( 0.5*dt*( ( - 1.0 ) / tau1 ) ) )*( - ( 0.0 ) / ( ( - 1.0 ) / tau1 ) - __primary );
    A += __primary;
  } else {
 A = A + factor1 * gnmdamax * dnmda * fnmda ;
     }
   if (nrn_netrec_state_adjust && !cvode_active_){
    /* discon state adjustment for cnexp case (rate uses no local variable) */
    double __state = B;
    double __primary = (B + factor1 * gnmdamax * dnmda * fnmda) - __state;
     __primary += ( 1. - exp( 0.5*dt*( ( - 1.0 ) / tau2 ) ) )*( - ( 0.0 ) / ( ( - 1.0 ) / tau2 ) - __primary );
    B += __primary;
  } else {
 B = B + factor1 * gnmdamax * dnmda * fnmda ;
     }
   if (nrn_netrec_state_adjust && !cvode_active_){
    /* discon state adjustment for cnexp case (rate uses no local variable) */
    double __state = C;
    double __primary = (C + factor2 * gampamax * dampa * fampa) - __state;
     __primary += ( 1. - exp( 0.5*dt*( ( - 1.0 ) / tau3 ) ) )*( - ( 0.0 ) / ( ( - 1.0 ) / tau3 ) - __primary );
    C += __primary;
  } else {
 C = C + factor2 * gampamax * dampa * fampa ;
     }
   if (nrn_netrec_state_adjust && !cvode_active_){
    /* discon state adjustment for cnexp case (rate uses no local variable) */
    double __state = D;
    double __primary = (D + factor2 * gampamax * dampa * fampa) - __state;
     __primary += ( 1. - exp( 0.5*dt*( ( - 1.0 ) / tau4 ) ) )*( - ( 0.0 ) / ( ( - 1.0 ) / tau4 ) - __primary );
    D += __primary;
  } else {
 D = D + factor2 * gampamax * dampa * fampa ;
     }
   if (nrn_netrec_state_adjust && !cvode_active_){
    /* discon state adjustment for cnexp case (rate uses no local variable) */
    double __state = dampa;
    double __primary = (dampa * decayampa) - __state;
     __primary += ( 1. - exp( 0.5*dt*( ( ( ( - 1.0 ) ) ) / taudampa ) ) )*( - ( ( ( 1.0 ) ) / taudampa ) / ( ( ( ( - 1.0 ) ) ) / taudampa ) - __primary );
    dampa += __primary;
  } else {
 dampa = dampa * decayampa ;
     }
   if (nrn_netrec_state_adjust && !cvode_active_){
    /* discon state adjustment for cnexp case (rate uses no local variable) */
    double __state = dnmda;
    double __primary = (dnmda * decaynmda) - __state;
     __primary += ( 1. - exp( 0.5*dt*( ( ( ( - 1.0 ) ) ) / taudnmda ) ) )*( - ( ( ( 1.0 ) ) / taudnmda ) / ( ( ( ( - 1.0 ) ) ) / taudnmda ) - __primary );
    dnmda += __primary;
  } else {
 dnmda = dnmda * decaynmda ;
     }
   if (nrn_netrec_state_adjust && !cvode_active_){
    /* discon state adjustment for cnexp case (rate uses no local variable) */
    double __state = fampa;
    double __primary = (fampa + facilampa) - __state;
     __primary += ( 1. - exp( 0.5*dt*( ( ( ( - 1.0 ) ) ) / taufampa ) ) )*( - ( ( ( 1.0 ) ) / taufampa ) / ( ( ( ( - 1.0 ) ) ) / taufampa ) - __primary );
    fampa += __primary;
  } else {
 fampa = fampa + facilampa ;
     }
   if (nrn_netrec_state_adjust && !cvode_active_){
    /* discon state adjustment for cnexp case (rate uses no local variable) */
    double __state = fnmda;
    double __primary = (fnmda + facilnmda) - __state;
     __primary += ( 1. - exp( 0.5*dt*( ( ( ( - 1.0 ) ) ) / taufnmda ) ) )*( - ( ( ( 1.0 ) ) / taufnmda ) / ( ( ( ( - 1.0 ) ) ) / taufnmda ) - __primary );
    fnmda += __primary;
  } else {
 fnmda = fnmda + facilnmda ;
     }
 } }
 
static void _net_init(Point_process* _pnt, double* _args, double _lflag) {
       double* _p = _pnt->_prop->param;
    Datum* _ppvar = _pnt->_prop->dparam;
    Datum* _thread = (Datum*)0;
    NrnThread* _nt = (NrnThread*)_pnt->_vnt;
 gampamax = _args[0] ;
   gnmdamax = _args[1] ;
   }
 
/*CVODE*/
 static int _ode_spec1 (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {int _reset = 0; {
   DA = - A / tau1 ;
   DB = - B / tau2 ;
   DC = - C / tau3 ;
   DD = - D / tau4 ;
   Ddampa = ( 1.0 - dampa ) / taudampa ;
   Ddnmda = ( 1.0 - dnmda ) / taudnmda ;
   Dfampa = ( 1.0 - fampa ) / taufampa ;
   Dfnmda = ( 1.0 - fnmda ) / taufnmda ;
   }
 return _reset;
}
 static int _ode_matsol1 (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {
 DA = DA  / (1. - dt*( ( - 1.0 ) / tau1 )) ;
 DB = DB  / (1. - dt*( ( - 1.0 ) / tau2 )) ;
 DC = DC  / (1. - dt*( ( - 1.0 ) / tau3 )) ;
 DD = DD  / (1. - dt*( ( - 1.0 ) / tau4 )) ;
 Ddampa = Ddampa  / (1. - dt*( ( ( ( - 1.0 ) ) ) / taudampa )) ;
 Ddnmda = Ddnmda  / (1. - dt*( ( ( ( - 1.0 ) ) ) / taudnmda )) ;
 Dfampa = Dfampa  / (1. - dt*( ( ( ( - 1.0 ) ) ) / taufampa )) ;
 Dfnmda = Dfnmda  / (1. - dt*( ( ( ( - 1.0 ) ) ) / taufnmda )) ;
  return 0;
}
 /*END CVODE*/
 static int state (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) { {
    A = A + (1. - exp(dt*(( - 1.0 ) / tau1)))*(- ( 0.0 ) / ( ( - 1.0 ) / tau1 ) - A) ;
    B = B + (1. - exp(dt*(( - 1.0 ) / tau2)))*(- ( 0.0 ) / ( ( - 1.0 ) / tau2 ) - B) ;
    C = C + (1. - exp(dt*(( - 1.0 ) / tau3)))*(- ( 0.0 ) / ( ( - 1.0 ) / tau3 ) - C) ;
    D = D + (1. - exp(dt*(( - 1.0 ) / tau4)))*(- ( 0.0 ) / ( ( - 1.0 ) / tau4 ) - D) ;
    dampa = dampa + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / taudampa)))*(- ( ( ( 1.0 ) ) / taudampa ) / ( ( ( ( - 1.0 ) ) ) / taudampa ) - dampa) ;
    dnmda = dnmda + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / taudnmda)))*(- ( ( ( 1.0 ) ) / taudnmda ) / ( ( ( ( - 1.0 ) ) ) / taudnmda ) - dnmda) ;
    fampa = fampa + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / taufampa)))*(- ( ( ( 1.0 ) ) / taufampa ) / ( ( ( ( - 1.0 ) ) ) / taufampa ) - fampa) ;
    fnmda = fnmda + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / taufnmda)))*(- ( ( ( 1.0 ) ) / taufnmda ) / ( ( ( ( - 1.0 ) ) ) / taufnmda ) - fnmda) ;
   }
  return 0;
}
 
static int _ode_count(int _type){ return 8;}
 
static void _ode_spec(NrnThread* _nt, Memb_list* _ml, int _type) {
   double* _p; Datum* _ppvar; Datum* _thread;
   Node* _nd; double _v; int _iml, _cntml;
  _cntml = _ml->_nodecount;
  _thread = _ml->_thread;
  for (_iml = 0; _iml < _cntml; ++_iml) {
    _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
    _nd = _ml->_nodelist[_iml];
    v = NODEV(_nd);
     _ode_spec1 (_p, _ppvar, _thread, _nt);
 }}
 
static void _ode_map(int _ieq, double** _pv, double** _pvdot, double* _pp, Datum* _ppd, double* _atol, int _type) { 
	double* _p; Datum* _ppvar;
 	int _i; _p = _pp; _ppvar = _ppd;
	_cvode_ieq = _ieq;
	for (_i=0; _i < 8; ++_i) {
		_pv[_i] = _pp + _slist1[_i];  _pvdot[_i] = _pp + _dlist1[_i];
		_cvode_abstol(_atollist, _atol, _i);
	}
 }
 
static void _ode_matsol_instance1(_threadargsproto_) {
 _ode_matsol1 (_p, _ppvar, _thread, _nt);
 }
 
static void _ode_matsol(NrnThread* _nt, Memb_list* _ml, int _type) {
   double* _p; Datum* _ppvar; Datum* _thread;
   Node* _nd; double _v; int _iml, _cntml;
  _cntml = _ml->_nodecount;
  _thread = _ml->_thread;
  for (_iml = 0; _iml < _cntml; ++_iml) {
    _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
    _nd = _ml->_nodelist[_iml];
    v = NODEV(_nd);
 _ode_matsol_instance1(_threadargs_);
 }}

static void initmodel(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {
  int _i; double _save;{
  A = A0;
  B = B0;
  C = C0;
  D = D0;
  dnmda = dnmda0;
  dampa = dampa0;
  fnmda = fnmda0;
  fampa = fampa0;
 {
   double _ltp1 , _ltp2 ;
 gnmda = 0.0 ;
   gampa = 0.0 ;
   A = 0.0 ;
   B = 0.0 ;
   C = 0.0 ;
   D = 0.0 ;
   dampa = 1.0 ;
   dnmda = 1.0 ;
   fampa = 1.0 ;
   fnmda = 1.0 ;
   _ltp1 = ( tau2 * tau1 ) / ( tau1 - tau2 ) * log ( tau1 / tau2 ) ;
   factor1 = - exp ( - _ltp1 / tau2 ) + exp ( - _ltp1 / tau1 ) ;
   factor1 = 1.0 / factor1 ;
   _ltp2 = ( tau4 * tau3 ) / ( tau3 - tau4 ) * log ( tau3 / tau4 ) ;
   factor2 = - exp ( - _ltp2 / tau4 ) + exp ( - _ltp2 / tau3 ) ;
   factor2 = 1.0 / factor2 ;
   }
 
}
}

static void nrn_init(NrnThread* _nt, Memb_list* _ml, int _type){
double* _p; Datum* _ppvar; Datum* _thread;
Node *_nd; double _v; int* _ni; int _iml, _cntml;
#if CACHEVEC
    _ni = _ml->_nodeindices;
#endif
_cntml = _ml->_nodecount;
_thread = _ml->_thread;
for (_iml = 0; _iml < _cntml; ++_iml) {
 _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
 _tsav = -1e20;
#if CACHEVEC
  if (use_cachevec) {
    _v = VEC_V(_ni[_iml]);
  }else
#endif
  {
    _nd = _ml->_nodelist[_iml];
    _v = NODEV(_nd);
  }
 v = _v;
 initmodel(_p, _ppvar, _thread, _nt);
}
}

static double _nrn_current(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt, double _v){double _current=0.;v=_v;{ {
   double _lcount ;
 gnmda = ( A - B ) / ( 1.0 + n * exp ( - gama * v ) ) ;
   gampa = ( C - D ) ;
   inmda = ( 1e-3 ) * gnmda * ( v - e ) ;
   iampa = ( 1e-3 ) * gampa * ( v - e ) ;
   }
 _current += inmda;
 _current += iampa;

} return _current;
}

static void nrn_cur(NrnThread* _nt, Memb_list* _ml, int _type) {
double* _p; Datum* _ppvar; Datum* _thread;
Node *_nd; int* _ni; double _rhs, _v; int _iml, _cntml;
#if CACHEVEC
    _ni = _ml->_nodeindices;
#endif
_cntml = _ml->_nodecount;
_thread = _ml->_thread;
for (_iml = 0; _iml < _cntml; ++_iml) {
 _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
#if CACHEVEC
  if (use_cachevec) {
    _v = VEC_V(_ni[_iml]);
  }else
#endif
  {
    _nd = _ml->_nodelist[_iml];
    _v = NODEV(_nd);
  }
 _g = _nrn_current(_p, _ppvar, _thread, _nt, _v + .001);
 	{ _rhs = _nrn_current(_p, _ppvar, _thread, _nt, _v);
 	}
 _g = (_g - _rhs)/.001;
 _g *=  1.e2/(_nd_area);
 _rhs *= 1.e2/(_nd_area);
#if CACHEVEC
  if (use_cachevec) {
	VEC_RHS(_ni[_iml]) -= _rhs;
  }else
#endif
  {
	NODERHS(_nd) -= _rhs;
  }
 
}
 
}

static void nrn_jacob(NrnThread* _nt, Memb_list* _ml, int _type) {
double* _p; Datum* _ppvar; Datum* _thread;
Node *_nd; int* _ni; int _iml, _cntml;
#if CACHEVEC
    _ni = _ml->_nodeindices;
#endif
_cntml = _ml->_nodecount;
_thread = _ml->_thread;
for (_iml = 0; _iml < _cntml; ++_iml) {
 _p = _ml->_data[_iml];
#if CACHEVEC
  if (use_cachevec) {
	VEC_D(_ni[_iml]) += _g;
  }else
#endif
  {
     _nd = _ml->_nodelist[_iml];
	NODED(_nd) += _g;
  }
 
}
 
}

static void nrn_state(NrnThread* _nt, Memb_list* _ml, int _type) {
double* _p; Datum* _ppvar; Datum* _thread;
Node *_nd; double _v = 0.0; int* _ni; int _iml, _cntml;
#if CACHEVEC
    _ni = _ml->_nodeindices;
#endif
_cntml = _ml->_nodecount;
_thread = _ml->_thread;
for (_iml = 0; _iml < _cntml; ++_iml) {
 _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
 _nd = _ml->_nodelist[_iml];
#if CACHEVEC
  if (use_cachevec) {
    _v = VEC_V(_ni[_iml]);
  }else
#endif
  {
    _nd = _ml->_nodelist[_iml];
    _v = NODEV(_nd);
  }
 v=_v;
{
 {   state(_p, _ppvar, _thread, _nt);
  }}}

}

static void terminal(){}

static void _initlists(){
 double _x; double* _p = &_x;
 int _i; static int _first = 1;
  if (!_first) return;
 _slist1[0] = A_columnindex;  _dlist1[0] = DA_columnindex;
 _slist1[1] = B_columnindex;  _dlist1[1] = DB_columnindex;
 _slist1[2] = C_columnindex;  _dlist1[2] = DC_columnindex;
 _slist1[3] = D_columnindex;  _dlist1[3] = DD_columnindex;
 _slist1[4] = dampa_columnindex;  _dlist1[4] = Ddampa_columnindex;
 _slist1[5] = dnmda_columnindex;  _dlist1[5] = Ddnmda_columnindex;
 _slist1[6] = fampa_columnindex;  _dlist1[6] = Dfampa_columnindex;
 _slist1[7] = fnmda_columnindex;  _dlist1[7] = Dfnmda_columnindex;
_first = 0;
}

#if NMODL_TEXT
static void register_nmodl_text_and_filename(int mech_type) {
    const char* nmodl_filename = "/gpfs/soma_fs/scratch/saka/project_src/in_silico_framework/mechanisms/channels_py3_wip/netglutamate.mod";
    const char* nmodl_file_text = 
  "COMMENT\n"
  "//****************************//\n"
  "// Created by Alon Polsky 	//\n"
  "//    apmega@yahoo.com		//\n"
  "//		2010			//\n"
  "//****************************//\n"
  "Modified 2015 by Robert Egger\n"
  "to include facilitation variable\n"
  "as modeled by Varela et al. 1997\n"
  "ENDCOMMENT\n"
  "\n"
  "TITLE NMDA synapse with depression\n"
  "\n"
  "\n"
  "NEURON {\n"
  "	POINT_PROCESS glutamate_syn\n"
  "	NONSPECIFIC_CURRENT inmda,iampa\n"
  "	RANGE gampamax,gnmdamax,inmda,iampa\n"
  "	RANGE decayampa,dampa,taudampa\n"
  "    RANGE decaynmda,dnmda,taudnmda\n"
  "    RANGE facilampa,fampa,taufampa\n"
  "    RANGE facilnmda,fnmda,taufnmda\n"
  "	RANGE gnmda,gampa\n"
  "	RANGE e,tau1,tau2,tau3,tau4\n"
  "}\n"
  "\n"
  "UNITS {\n"
  "	(nA) 	= (nanoamp)\n"
  "	(mV)	= (millivolt)\n"
  "	(nS) 	= (nanomho)\n"
  "	(mM)    = (milli/liter)\n"
  " 	(mA) = (milliamp)\n"
  "	(um) = (micron)\n"
  "}\n"
  "\n"
  "PARAMETER {\n"
  "	gnmdamax=1	(nS)\n"
  "	gampamax=1	(nS)\n"
  "	e= 0.0	(mV)\n"
  "	tau1=50	(ms)	: NMDA inactivation\n"
  "	tau2=2	(ms)	: NMDA activation\n"
  "	tau3=2	(ms)	: AMPA inactivation\n"
  "	tau4=0.1	(ms)	: AMPA activation\n"
  "	tau_ampa=2	(ms)	\n"
  "	n=0.25 	(/mM)	    : Schiller and Larkum\n"
  "	gama=0.08 	(/mV)   : Schiller and Larkum\n"
  "	:n=0.28      (/mM)   : Jahr and Stevens\n"
  "	:gama=0.062  (/mV)   : Jahr and Stevens\n"
  "	dt 		(ms)\n"
  "	v		(mV)\n"
  "	decayampa=.5\n"
  "	decaynmda=.5\n"
  "	taudampa=200	(ms):tau decay\n"
  "	taudnmda=200	(ms):tau decay\n"
  "    taufampa=200    (ms)\n"
  "    facilampa=0.0\n"
  "    taufnmda=200    (ms)\n"
  "    facilnmda=0.0\n"
  "}\n"
  "\n"
  "ASSIGNED { \n"
  "	inmda		(nA)  \n"
  "	iampa		(nA)  \n"
  "	gnmda		(nS)\n"
  "	gampa		(nS)\n"
  "	factor1		: NMDA normalization factor\n"
  "	factor2		: AMPA normalization factor\n"
  "\n"
  "}\n"
  "STATE {\n"
  "	A 		(nS)\n"
  "	B 		(nS)\n"
  "	C 		(nS)\n"
  "	D 		(nS)\n"
  "	dampa\n"
  "	dnmda\n"
  "    fampa\n"
  "    fnmda\n"
  "}\n"
  "\n"
  "\n"
  "INITIAL {\n"
  "	LOCAL tp1, tp2\n"
  "    gnmda=0 \n"
  "    gampa=0 \n"
  "	A=0\n"
  "	B=0\n"
  "	C=0\n"
  "	D=0\n"
  "	dampa=1\n"
  "	dnmda=1\n"
  "    fampa=1\n"
  "    fnmda=1\n"
  "	\n"
  "	tp1 = (tau2*tau1)/(tau1 - tau2) * log(tau1/tau2)\n"
  "	factor1 = -exp(-tp1/tau2) + exp(-tp1/tau1)\n"
  "	factor1 = 1/factor1\n"
  "	\n"
  "	tp2 = (tau4*tau3)/(tau3 - tau4) * log(tau3/tau4)\n"
  "	factor2 = -exp(-tp2/tau4) + exp(-tp2/tau3)\n"
  "	factor2 = 1/factor2\n"
  "}    \n"
  "\n"
  "BREAKPOINT {  \n"
  "    \n"
  "	LOCAL count\n"
  "	SOLVE state METHOD cnexp\n"
  "	gnmda=(A-B)/(1+n*exp(-gama*v) )\n"
  "	gampa=(C-D)\n"
  "	inmda =(1e-3)*gnmda*(v-e)\n"
  "	iampa= (1e-3)*gampa*(v- e)\n"
  "\n"
  "}\n"
  "NET_RECEIVE(weight_ampa, weight_nmda) {\n"
  " \n"
  "	INITIAL {\n"
  "	  gampamax = weight_ampa\n"
  "	  gnmdamax = weight_nmda\n"
  "	}\n"
  "	gampamax = weight_ampa\n"
  "	gnmdamax = weight_nmda\n"
  "	\n"
  "	A = A+ factor1*gnmdamax*dnmda*fnmda\n"
  "	B = B+ factor1*gnmdamax*dnmda*fnmda\n"
  "	C = C+ factor2*gampamax*dampa*fampa\n"
  "	D = D+ factor2*gampamax*dampa*fampa\n"
  "	:gampa = gampa+ gampamax*dampa\n"
  "	dampa = dampa* decayampa\n"
  "	dnmda = dnmda* decaynmda\n"
  "    fampa = fampa + facilampa\n"
  "    fnmda = fnmda + facilnmda\n"
  "	\n"
  ":	VERBATIM\n"
  ":	/*\n"
  ":	printf(\"***********\\n\");\n"
  ":	printf(\"A = %.2f\\n\", A);\n"
  ":	printf(\"B = %.2f\\n\", B);\n"
  ":	printf(\"C = %.2f\\n\", C);\n"
  ":	printf(\"D = %.2f\\n\", D);\n"
  ":	*/\n"
  ":	ENDVERBATIM\n"
  "}\n"
  "DERIVATIVE state {\n"
  "	A'=-A/tau1\n"
  "	B'=-B/tau2\n"
  "	C'=-C/tau3\n"
  "	D'=-D/tau4\n"
  "	dampa'=(1-dampa)/taudampa\n"
  "	dnmda'=(1-dnmda)/taudnmda\n"
  "    fampa'=(1-fampa)/taufampa\n"
  "    fnmda'=(1-fnmda)/taufnmda\n"
  "}\n"
  "\n"
  "\n"
  "\n"
  "\n"
  "\n"
  ;
    hoc_reg_nmodl_filename(mech_type, nmodl_filename);
    hoc_reg_nmodl_text(mech_type, nmodl_file_text);
}
#endif
